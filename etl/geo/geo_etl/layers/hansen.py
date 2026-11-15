import math

import geopandas as gpd
import numpy as np

from geo_etl import raster
from geo_etl.catalog import HANSEN
from geo_etl.layers import Options, Result, by_district, download, failure
from geo_etl.rows import Rows, pick

VERSION = "GFC-2025-v1.13"
BASE = f"https://storage.googleapis.com/earthenginepartners-hansen/{VERSION}"
LAST_YEAR = 2025
CANOPY = 30


def tile_id(top: int, left: int) -> str:
    ns = "N" if top >= 0 else "S"
    ew = "E" if left >= 0 else "W"
    return f"{abs(top):02d}{ns}_{abs(left):03d}{ew}"


def tile_ids(bounds: tuple[float, float, float, float]) -> list[str]:
    xmin, ymin, xmax, ymax = bounds
    tops = range(math.floor(ymin / 10) * 10 + 10, math.floor(ymax / 10) * 10 + 11, 10)
    lefts = range(math.floor(xmin / 10) * 10, math.floor(xmax / 10) * 10 + 1, 10)
    return [tile_id(top, left) for top in tops for left in lefts]


def layer_urls(layer: str, bounds, options: Options) -> list[str]:
    urls = [f"{BASE}/Hansen_{VERSION}_{layer}_{t}.tif" for t in tile_ids(bounds)]
    if not options.download_striped:
        return urls
    local = []
    for url in urls:
        if raster.exists(url):
            local.append(str(download(url, options.cache / "hansen" / url.rsplit("/", 1)[1])))
    return local


def classify(treecover: np.ndarray, lossyear: np.ndarray, datamask: np.ndarray) -> np.ndarray:
    land = datamask == 1
    forest = treecover >= CANOPY
    lost = np.nan_to_num(lossyear, nan=0.0) > 0
    code = np.where(forest, np.where(lost, 100.0 + np.nan_to_num(lossyear, nan=0.0), 1.0), 0.0)
    return np.where(land, code, np.nan).astype("float32")


def run(districts: gpd.GeoDataFrame, options: Options) -> Result:
    factor = max(1, options.hansen_factor)
    effective = "1 arc-second (about 30 m)" if factor == 1 else f"{factor} arc-seconds (decimated, nearest)"
    rows = Rows(
        HANSEN,
        f"exactextract coverage weight area_spherical_km2 at {effective}; land pixels (datamask = 1) only; "
        f"forest = treecover2000 >= {CANOPY}%; loss counted inside 2000 forest by lossyear",
    )
    failures: list[dict] = []
    for group in by_district(districts):
        district = group.iloc[0]
        try:
            bounds = raster.bounds_in(group, "EPSG:4326", 0.005)
            grids = {}
            for layer in ("treecover2000", "lossyear", "datamask"):
                grid = raster.read(layer_urls(layer, bounds, options), bounds, factor=factor, dtype="float32")
                if grid is None:
                    raise RuntimeError(f"{layer} tile not reachable")
                grids[layer] = grid
            tc = grids["treecover2000"]
            land = grids["datamask"].values == 1
            code = classify(tc.values, grids["lossyear"].values, grids["datamask"].values)
            cover = raster.Grid(np.where(land, tc.values, np.nan).astype("float32"), tc.transform, tc.crs)
            classes = raster.Grid(code, tc.transform, tc.crs)
            mean = raster.zonal(cover, group, ["mean=mean(coverage_weight=area_spherical_km2)", "pixels=count"])
            record = raster.zonal(
                classes,
                group,
                [
                    "classes=unique",
                    "shares=frac(coverage_weight=area_spherical_km2)",
                    "area=count(coverage_weight=area_spherical_km2)",
                    "pixels=count",
                ],
            ).iloc[0]
            pixels = float(record["pixels"])
            land_km2 = float(record["area"])
            found = {
                int(c): float(s)
                for c, s in zip(
                    np.asarray(pick(record, "classes"), dtype=float), np.asarray(pick(record, "shares")), strict=True
                )
            }
            forest_share = sum(s for c, s in found.items() if c >= 1)
            rows.add(
                district, "treecover2000", "2000", "DISTRICT_MEAN", float(mean.iloc[0]["mean"]), "%", pixels=pixels
            )
            rows.add(
                district, f"forest_canopy{CANOPY}", "2000", "SHARE", forest_share, "fraction of land", pixels=pixels
            )
            rows.add(
                district, f"forest_canopy{CANOPY}_area", "2000", "TOTAL", forest_share * land_km2, "km2", pixels=pixels
            )
            total_loss = 0.0
            for year in range(2001, LAST_YEAR + 1):
                loss = found.get(100 + year - 2000, 0.0) * land_km2
                total_loss += loss
                rows.add(district, f"forest_loss_canopy{CANOPY}", str(year), "TOTAL", loss, "km2", pixels=pixels)
            period = f"2001-{LAST_YEAR}"
            rows.add(district, f"forest_loss_canopy{CANOPY}", period, "TOTAL", total_loss, "km2", pixels=pixels)
            if forest_share > 0:
                rows.add(
                    district,
                    f"forest_loss_canopy{CANOPY}_share",
                    period,
                    "SHARE",
                    total_loss / (forest_share * land_km2),
                    "fraction of 2000 forest",
                    pixels=pixels,
                )
        except Exception as error:
            failures.append(failure(group, "hansen", error))
    return Result(HANSEN, rows.frame(), failures=failures)
