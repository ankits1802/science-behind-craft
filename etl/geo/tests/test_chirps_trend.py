import re

import pytest
from test_chirps_normals import constant_grid, kachchh

from geo_etl import raster
from geo_etl.layers import Options, chirps

ANNUAL = re.compile(r"chirps-v3\.0\.(\d{4})\.tif$")
FIRST = 1996


def rising_annual_totals(missing_year: int | None = None):
    def read(urls, bounds, **kwargs):
        year = int(ANNUAL.search(urls[0])[1])
        return None if year == missing_year else constant_grid(500.0 + 3.0 * (year - FIRST))

    return read


@pytest.fixture
def thirty_years(monkeypatch, tmp_path):
    monkeypatch.setattr(chirps, "latest_year", lambda: 2025)
    return Options(cache=tmp_path, climate_first_year=FIRST, chirps_monthly=False)


def by_key(result):
    return result.values.set_index(["variable", "depthOrPeriod", "stat"])


def test_thirty_years_of_rain_give_the_normal_and_the_trend_over_the_dataset_period(monkeypatch, thirty_years):
    monkeypatch.setattr(raster, "read", rising_annual_totals())
    result = chirps.run(kachchh(), thirty_years)
    assert result.failures == []
    assert result.dataset.period == "1996-2025"
    values = by_key(result)
    assert values.loc[("annual_precipitation", "1996-2025", "NORMAL"), "value"] == pytest.approx(543.5)
    slope = values.loc[("annual_precipitation", "1996-2025", "TREND_PER_DECADE")]
    assert (slope["value"], slope["unit"]) == (pytest.approx(30.0), "mm/year per decade")
    p_value = values.loc[("annual_precipitation", "1996-2025", "TREND_P_VALUE")]
    assert p_value["value"] < 0.05 and p_value["unit"] == "p-value"
    yearly = result.values[(result.values["stat"] == "DISTRICT_MEAN")]
    assert yearly["depthOrPeriod"].tolist() == [str(year) for year in range(1996, 2026)]


def test_a_district_missing_a_year_has_its_years_but_no_normal_or_trend(monkeypatch, thirty_years):
    monkeypatch.setattr(raster, "read", rising_annual_totals(missing_year=2010))
    result = chirps.run(kachchh(), thirty_years)
    assert [failure["step"] for failure in result.failures] == ["chirps annual 2010"]
    stats = set(result.values["stat"])
    assert "DISTRICT_MEAN" in stats
    assert not stats & {"NORMAL", "TREND_PER_DECADE", "TREND_P_VALUE"}


def test_two_years_give_normals_but_no_trend(monkeypatch, tmp_path):
    monkeypatch.setattr(chirps, "latest_year", lambda: 2025)
    monkeypatch.setattr(raster, "read", rising_annual_totals())
    result = chirps.run(kachchh(), Options(cache=tmp_path, climate_first_year=2024, chirps_monthly=False))
    assert "NORMAL" in set(result.values["stat"])
    assert not set(result.values["stat"]) & {"TREND_PER_DECADE", "TREND_P_VALUE"}


def test_a_run_cannot_start_before_the_chirps_record():
    with pytest.raises(RuntimeError, match="runs from 1981"):
        chirps.run_years(1980, 2025)
