import geopandas as gpd
import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin
from shapely.geometry import box

from geo_etl import raster


def grid_of(values: np.ndarray) -> raster.Grid:
    rows, _ = values.shape
    return raster.Grid(values.astype("float32"), from_origin(0, rows, 1, 1), CRS.from_epsg(3857))


def zone(*bounds: float) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"districtLgd": [1]}, geometry=[box(*bounds)], crs="EPSG:3857")


def test_weighted_quantile_follows_weights_on_ties():
    values = np.r_[np.zeros(95), np.full(5, 20.0)]
    weights = np.ones(100)
    assert raster.weighted_quantile(values, weights, 0.1) == 0.0
    assert raster.weighted_quantile(values, weights, 0.9) == 0.0
    assert raster.weighted_quantile(values, weights, 0.96) == 20.0


def test_weighted_quantile_ignores_nan_and_zero_weight():
    values = np.array([np.nan, 1.0, 2.0, 100.0])
    weights = np.array([5.0, 1.0, 1.0, 0.0])
    assert raster.weighted_quantile(values, weights, 0.9) == 2.0
    assert np.isnan(raster.weighted_quantile(np.array([np.nan]), np.array([1.0]), 0.5))


def test_zonal_quantiles_bracket_the_mean_on_tied_data():
    values = np.zeros((10, 10))
    values[0, :5] = 20
    table = raster.zonal(grid_of(values), zone(0, 0, 10, 10), raster.continuous_ops(grid_of(values)))
    record = table.iloc[0]
    assert raster.CELL_VALUES not in table.columns
    assert raster.CELL_WEIGHTS not in table.columns
    assert record["p10"] == 0.0
    assert record["p90"] == 0.0
    assert record["mean"] == pytest.approx(1.0)


def test_zonal_quantiles_skip_nodata_cells():
    values = np.arange(16, dtype="float64").reshape(4, 4)
    values[0, 0] = np.nan
    table = raster.zonal(grid_of(values), zone(0, 0, 4, 4), raster.continuous_ops(grid_of(values)))
    record = table.iloc[0]
    assert record["p10"] == 2.0
    assert record["p90"] == 14.0
    assert record["pixels"] == pytest.approx(15.0)
