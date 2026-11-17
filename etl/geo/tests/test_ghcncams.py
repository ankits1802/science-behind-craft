import datetime as dt

import geopandas as gpd
import numpy as np
import pytest
from netcdf_classic import Variable, write_classic
from shapely.geometry import box

from geo_etl.layers import Options, ghcncams

HOURS_UNITS = "hours since 1800-01-01 00:00:0.0"
MISSING = -9.96921e36
FIRST, LAST_COMPLETE = 1994, 2025
WEST, NORTH, CELL, SIDE = 67.0, 25.0, 0.5, 14
SEA_CELL = (1, 4)


def month_starts() -> list[tuple[int, int]]:
    months = [(year, month) for year in range(FIRST, LAST_COMPLETE + 1) for month in range(1, 13)]
    return [*months, (2026, 1), (2026, 2), (2026, 3)]


def kelvin(year: int, month: int) -> float:
    return 300.15 + 0.05 * (year - 1996) + (month - 6.5)


def tiny_file(tmp_path):
    months = month_starts()
    hours = [(dt.datetime(y, m, 1) - dt.datetime(1800, 1, 1)).total_seconds() / 3600 for y, m in months]
    air = np.stack([np.full((SIDE, SIDE), kelvin(y, m)) for y, m in months]).astype(">f4")
    air[:, SEA_CELL[0], SEA_CELL[1]] = MISSING
    lats = NORTH - CELL / 2 - CELL * np.arange(SIDE)
    lons = WEST + CELL / 2 + CELL * np.arange(SIDE)
    variables = [
        Variable("time", ("time",), np.asarray(hours, dtype=">f8"), {"units": HOURS_UNITS}),
        Variable("lat", ("lat",), lats.astype(">f4"), {"units": "degrees_north"}),
        Variable("lon", ("lon",), lons.astype(">f4"), {"units": "degrees_east"}),
        Variable("air", ("time", "lat", "lon"), air, {"units": "degK"}),
    ]
    return write_classic(tmp_path / "air.mon.mean.nc", {"time": len(months), "lat": SIDE, "lon": SIDE}, variables)


def districts() -> gpd.GeoDataFrame:
    sea_west = WEST + CELL * SEA_CELL[1]
    sea_north = NORTH - CELL * SEA_CELL[0]
    return gpd.GeoDataFrame(
        {"districtLgd": [449, 9001], "stateLgd": [24, 24], "districtName": ["Kachchh", "Sea"]},
        geometry=[box(70.2, 20.2, 71.8, 21.8), box(sea_west + 0.1, sea_north - 0.4, sea_west + 0.4, sea_north - 0.1)],
        crs="EPSG:4326",
    )


def test_band_times_name_their_months():
    assert ghcncams.month_keys([1297320.0, 1298064.0], HOURS_UNITS) == ((1948, 1), (1948, 2))
    assert ghcncams.month_keys([31.0], "days since 2025-12-01") == ((2026, 1),)


def test_months_must_follow_each_other():
    with pytest.raises(RuntimeError, match="not consecutive"):
        ghcncams.month_keys([1297320.0, 1298808.0], HOURS_UNITS)
    with pytest.raises(RuntimeError, match="not hours or days"):
        ghcncams.month_keys([1.0], "months since 1800-01-01")


def test_only_complete_years_from_the_first_year_are_used():
    assert ghcncams.complete_years(month_starts(), 1996) == range(1996, 2026)
    gap = [key for key in month_starts() if key != (2000, 7)]
    with pytest.raises(RuntimeError, match="no complete run"):
        ghcncams.complete_years(gap, 1996)
    with pytest.raises(RuntimeError, match="starts in 1948"):
        ghcncams.complete_years(month_starts(), 1940)


def test_kelvin_outside_the_valid_range_is_no_data():
    shown = ghcncams.celsius(np.array([300.15, MISSING, 120.0]), "degK")
    assert shown[0] == pytest.approx(27.0)
    assert np.isnan(shown[1:]).all()
    with pytest.raises(RuntimeError, match="not Kelvin"):
        ghcncams.celsius(np.array([27.0]), "degC")


def test_the_netcdf_file_is_read_through_gdal_with_its_months_and_grid(tmp_path):
    grids = ghcncams.read_months(tiny_file(tmp_path), (69.0, 19.5, 72.5, 23.0))
    assert grids.months[0] == (FIRST, 1) and grids.months[-1] == (2026, 3)
    assert (grids.transform.a, grids.transform.e) == (CELL, -CELL)
    assert (grids.transform.c, grids.transform.f) == (69.0, 23.0)
    july = grids.months.index((2000, 7))
    assert grids.celsius[july, 0, 0] == pytest.approx(kelvin(2000, 7) - 273.15, abs=1e-4)


def test_the_layer_writes_each_year_the_normal_and_the_trend_per_district(monkeypatch, tmp_path):
    path = tiny_file(tmp_path)
    monkeypatch.setattr(ghcncams, "download", lambda url, target: path)
    result = ghcncams.run(districts(), Options(cache=tmp_path, climate_first_year=FIRST))
    assert result.failures == [] and result.dataset.period == "1994-2025"
    rows = result.values.set_index(["districtLgd", "variable", "depthOrPeriod", "stat"])
    kachchh = rows.loc[449, "annual_mean_temperature"]
    assert kachchh.loc[("1996", "DISTRICT_MEAN"), "value"] == pytest.approx(27.0, abs=1e-4)
    assert kachchh.loc[("1994-2025", "NORMAL"), "value"] == pytest.approx(27.0 + 0.05 * 13.5, abs=1e-4)
    slope = kachchh.loc[("1994-2025", "TREND_PER_DECADE")]
    assert (slope["value"], slope["unit"]) == (pytest.approx(0.5, abs=1e-4), "degC per decade")
    assert kachchh.loc[("1994-2025", "TREND_P_VALUE"), "value"] < 0.05
    assert 9001 not in set(result.values["districtLgd"])
    assert result.districts_without_cells == [9001]
