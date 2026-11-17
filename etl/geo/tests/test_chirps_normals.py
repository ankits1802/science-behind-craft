import re

import geopandas as gpd
import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin
from shapely.geometry import box

from geo_etl import raster
from geo_etl.layers import Options, chirps

MONTHLY = re.compile(r"chirps-v3\.0\.(\d{4})\.(\d{2})\.tif$")
ANNUAL = re.compile(r"chirps-v3\.0\.(\d{4})\.tif$")
ANNUAL_TOTALS = {2024: 700.0, 2025: 900.0}


def month_total(year: int, month: int) -> float:
    return 10.0 * month + 4.0 * (year - 2024)


def constant_grid(value: float) -> raster.Grid:
    return raster.Grid(np.full((4, 4), value, dtype="float32"), from_origin(70.0, 24.0, 1.0, 1.0), CRS.from_epsg(4326))


def tiny_chirps(missing: str | None = None):
    def read(urls, bounds, **kwargs):
        url = urls[0]
        if missing and url.endswith(missing):
            return None
        if found := MONTHLY.search(url):
            return constant_grid(month_total(int(found[1]), int(found[2])))
        return constant_grid(ANNUAL_TOTALS[int(ANNUAL.search(url)[1])])

    return read


def kachchh() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"districtLgd": [449], "stateLgd": [24], "districtName": ["Kachchh"]},
        geometry=[box(70.2, 20.2, 71.8, 21.8)],
        crs="EPSG:4326",
    )


@pytest.fixture
def two_years(monkeypatch, tmp_path):
    monkeypatch.setattr(chirps, "latest_year", lambda: 2025)
    return Options(cache=tmp_path, chirps_years=2)


def test_twelve_monthly_normals_are_the_mean_of_each_month_over_the_period(monkeypatch, two_years):
    monkeypatch.setattr(raster, "read", tiny_chirps())
    result = chirps.run(kachchh(), two_years)
    assert result.failures == []
    assert result.dataset.period == "2024-2025"
    rows = result.values[result.values["variable"] == "monthly_precipitation"]
    assert rows["depthOrPeriod"].tolist() == [f"2024-2025-{m:02d}" for m in range(1, 13)]
    assert rows["value"].tolist() == pytest.approx([10.0 * m + 2.0 for m in range(1, 13)])
    assert set(rows["stat"]) == {"NORMAL"}
    assert set(rows["unit"]) == {"mm/month"}
    assert set(rows["resolution"]) == {"0.05 degree"}
    assert set(rows["districtLgd"]) == {449}


def test_the_annual_normal_and_monsoon_share_come_from_the_same_years(monkeypatch, two_years):
    monkeypatch.setattr(raster, "read", tiny_chirps())
    values = chirps.run(kachchh(), two_years).values.set_index(["variable", "depthOrPeriod", "stat"])["value"]
    assert values[("annual_precipitation", "2024-2025", "NORMAL")] == pytest.approx(800.0)
    assert values[("annual_precipitation_cv", "2024-2025", "NORMAL")] == pytest.approx(0.125)
    assert values[("monsoon_share_jjas", "2024-2025", "NORMAL")] == pytest.approx(308.0 / 804.0)


def test_a_month_that_cannot_be_read_leaves_every_district_without_monthly_normals(monkeypatch, two_years):
    monkeypatch.setattr(raster, "read", tiny_chirps(missing="chirps-v3.0.2025.07.tif"))
    result = chirps.run(kachchh(), two_years)
    assert [failure["step"] for failure in result.failures] == ["chirps monthly 2025-07"]
    variables = set(result.values["variable"])
    assert "monthly_precipitation" not in variables
    assert "monsoon_share_jjas" not in variables
    assert "annual_precipitation" in variables
