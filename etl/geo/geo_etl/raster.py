import functools
import math
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from exactextract import exact_extract
from exactextract.raster import NumPyRasterSource
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.errors import RasterioIOError
from rasterio.merge import merge
from rasterio.transform import Affine

GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF,.vrt,.ovr",
    "GDAL_HTTP_MULTIRANGE": "YES",
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "GDAL_HTTP_MAX_RETRY": "5",
    "GDAL_HTTP_RETRY_DELAY": "3",
    "GDAL_HTTP_TIMEOUT": "120",
    "VSI_CACHE": "TRUE",
    "VSI_CACHE_SIZE": "268435456",
    "GDAL_CACHEMAX": "1024",
    "CPL_VSIL_CURL_CACHE_SIZE": "536870912",
}


def gdal_env() -> rasterio.Env:
    overrides = {k: os.environ.get(k, v) for k, v in GDAL_ENV.items()}
    return rasterio.Env(**{k: int(v) if v.isdigit() else v for k, v in overrides.items()})


def vsicurl(url: str) -> str:
    return url if url.startswith("/vsi") or not url.startswith("http") else "/vsicurl/" + url


@functools.cache
def exists(url: str) -> bool:
    try:
        with gdal_env(), rasterio.open(vsicurl(url)):
            return True
    except RasterioIOError:
        return False


def crs_of(url: str) -> CRS:
    with gdal_env(), rasterio.open(vsicurl(url)) as dataset:
        return dataset.crs


@dataclass
class Grid:
    values: np.ndarray
    transform: Affine
    crs: CRS

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        rows, cols = self.values.shape
        xmin, ymax = self.transform.c, self.transform.f
        xmax = xmin + cols * self.transform.a
        ymin = ymax + rows * self.transform.e
        return xmin, ymin, xmax, ymax

    @property
    def resolution(self) -> tuple[float, float]:
        return abs(self.transform.a), abs(self.transform.e)

    def source(self) -> NumPyRasterSource:
        xmin, ymin, xmax, ymax = self.bounds
        return NumPyRasterSource(self.values, xmin, ymin, xmax, ymax, srs_wkt=self.crs.to_wkt())


def read(
    urls: Sequence[str],
    bounds: tuple[float, float, float, float],
    *,
    factor: int = 1,
    resampling: Resampling = Resampling.nearest,
    nodata_values: Iterable[float] = (),
    valid_min: float | None = None,
    scale: float | None = None,
    offset: float | None = None,
    dtype: str = "float32",
) -> Grid | None:
    present = [u for u in urls if exists(u)]
    if not present:
        return None
    with gdal_env():
        datasets = [rasterio.open(vsicurl(u)) for u in present]
        try:
            first = datasets[0]
            rx, ry = first.res
            res = (rx * factor, ry * factor)
            origin = (first.transform.c, first.transform.f)
            snapped = snap_bounds(bounds, origin, res)
            native_nodata = first.nodata
            fill = native_nodata if native_nodata is not None else _fill_for(first.dtypes[0])
            array, transform = merge(
                datasets,
                bounds=snapped,
                res=res,
                nodata=fill,
                resampling=resampling,
                indexes=[1],
            )
            crs = first.crs
            file_scale = first.scales[0] if first.scales else 1.0
            file_offset = first.offsets[0] if first.offsets else 0.0
        finally:
            for ds in datasets:
                ds.close()
    raw = array[0]
    mask = np.isnan(raw) if np.isnan(fill) else raw == fill
    for value in nodata_values:
        mask |= raw == value
    values = raw.astype("float64")
    values = values * (file_scale if scale is None else scale) + (file_offset if offset is None else offset)
    if valid_min is not None:
        mask |= values < valid_min
    values[mask] = np.nan
    return Grid(values=values.astype(dtype), transform=transform, crs=crs)


def _fill_for(dtype: str) -> float:
    kind = np.dtype(dtype)
    if kind.kind == "u":
        return float(np.iinfo(kind).max)
    if kind.kind == "i":
        return float(np.iinfo(kind).min)
    return float("nan")


def bounds_in(frame: gpd.GeoDataFrame, crs: CRS | str, pad: float = 0.0) -> tuple[float, float, float, float]:
    xmin, ymin, xmax, ymax = frame.to_crs(crs).total_bounds
    return xmin - pad, ymin - pad, xmax + pad, ymax + pad


def snap_bounds(
    bounds: tuple[float, float, float, float], origin: tuple[float, float], step: tuple[float, float]
) -> tuple[float, float, float, float]:
    ox, oy = origin
    sx, sy = step
    xmin = ox + math.floor((bounds[0] - ox) / sx) * sx
    xmax = ox + math.ceil((bounds[2] - ox) / sx) * sx
    ymin = oy + math.floor((bounds[1] - oy) / sy) * sy
    ymax = oy + math.ceil((bounds[3] - oy) / sy) * sy
    return xmin, ymin, xmax, ymax


def zonal(grid: Grid, frame: gpd.GeoDataFrame, ops: list[str]) -> pd.DataFrame:
    local = frame[["districtLgd", "geometry"]].to_crs(grid.crs)
    result = exact_extract(grid.source(), local, ops, include_cols=["districtLgd"], output="pandas")
    return pd.DataFrame(result)


def geographic(grid: Grid) -> bool:
    return bool(grid.crs.is_geographic)


def weight(grid: Grid) -> str:
    return "area_spherical_km2" if geographic(grid) else "area_cartesian"


def continuous_ops(grid: Grid) -> list[str]:
    w = weight(grid)
    return [
        f"mean=mean(coverage_weight={w})",
        f"p10=quantile(q=0.1,coverage_weight={w})",
        f"p90=quantile(q=0.9,coverage_weight={w})",
        "pixels=count(coverage_weight=fraction)",
    ]


def class_ops(grid: Grid) -> list[str]:
    w = weight(grid)
    return ["classes=unique", f"shares=frac(coverage_weight={w})", "pixels=count(coverage_weight=fraction)"]


def describe(grid: Grid) -> str:
    rx, ry = grid.resolution
    unit = "degree" if geographic(grid) else "m"
    return f"{rx:.8g} x {ry:.8g} {unit} grid"
