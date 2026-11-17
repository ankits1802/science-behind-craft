import dataclasses
import logging

import pytest

from app.geo.climate import TREND_DATASETS, climate_trends
from app.geo.records import DatasetRecord, ValueRecord
from app.research.blocks_insight import TREND_SIGNIFICANCE
from app.research.blocks_place import DistrictRef

from ..contracts.phase_b_golden import catalog_dataset
from .golden_region import dataset_record

KACHCHH = DistrictRef(district_lgd=449, name="Kachchh", state_name="Gujarat")
BARMER = DistrictRef(district_lgd=99, name="Barmer", state_name="Rajasthan")
PERIOD = "1981-2025"
CHIRPS = "CHIRPS_3_0"
GHCN = "GHCN_CAMS_T2M"


def dataset(code: str, period: str = PERIOD) -> DatasetRecord:
    return dataset_record(catalog_dataset(code) | {"period": period})


def row(stat: str, value: float, unit: str, **changes: object) -> ValueRecord:
    fields: dict[str, object] = {
        "district_lgd": 449,
        "dataset_code": CHIRPS,
        "variable": "annual_precipitation",
        "depth_or_period": PERIOD,
        "stat": stat,
        "value": value,
        "value_text": None,
        "unit": unit,
        "resolution": None,
        "method": "Theil-Sen slope",
    }
    return ValueRecord(**(fields | changes))


def kachchh_rain(**changes: object) -> list[ValueRecord]:
    return [
        row("NORMAL", 383.0, "mm/year", **changes),
        row("TREND_PER_DECADE", 21.6, "mm/year per decade", **changes),
        row("TREND_P_VALUE", 0.12, "p-value", **changes),
    ]


def kachchh_heat() -> list[ValueRecord]:
    heat = {"dataset_code": GHCN, "variable": "annual_mean_temperature"}
    return [
        row("NORMAL", 26.9, "degC", **heat),
        row("TREND_PER_DECADE", 0.21, "degC per decade", **heat),
        row("TREND_P_VALUE", 0.003, "p-value", **heat),
    ]


def test_a_district_s_stored_trends_are_read_with_their_dataset_rows() -> None:
    datasets = {CHIRPS: dataset(CHIRPS), GHCN: dataset(GHCN)}
    found = climate_trends([KACHCHH], [*kachchh_rain(), *kachchh_heat()], datasets)
    rain, heat = found.trends
    assert (rain.district, rain.variable, rain.dataset_code, rain.period) == (
        KACHCHH,
        "annual_precipitation",
        CHIRPS,
        PERIOD,
    )
    assert (rain.mean, rain.slope_per_decade, rain.p_value, rain.significant) == (383.0, 21.6, 0.12, False)
    assert (rain.resolution, rain.mean_unit, rain.slope_unit) == (
        "0.05 degree",
        "mm/year",
        "mm/year per decade",
    )
    assert (heat.slope_per_decade, heat.significant, heat.resolution) == (0.21, True, "0.5 degree")
    assert [d.code for d in found.datasets] == [CHIRPS, GHCN]
    assert [d.period for d in found.datasets] == [PERIOD, PERIOD]


def test_a_district_without_data_shows_no_trend() -> None:
    datasets = {CHIRPS: dataset(CHIRPS)}
    found = climate_trends([BARMER, KACHCHH], kachchh_rain(), datasets)
    assert [trend.district for trend in found.trends] == [KACHCHH]
    assert climate_trends([BARMER], kachchh_rain(), datasets).trends == ()
    assert climate_trends([BARMER], kachchh_rain(), datasets).datasets == ()


def test_a_trend_missing_a_statistic_is_not_shown() -> None:
    partial = [value for value in kachchh_rain() if value.stat != "TREND_P_VALUE"]
    assert climate_trends([KACHCHH], partial, {CHIRPS: dataset(CHIRPS)}).trends == ()


def test_only_the_trend_over_the_dataset_row_s_period_is_shown() -> None:
    older = kachchh_rain(depth_or_period="1981-2024")
    assert climate_trends([KACHCHH], older, {CHIRPS: dataset(CHIRPS)}).trends == ()


def test_a_series_shorter_than_thirty_years_is_no_trend(caplog: pytest.LogCaptureFixture) -> None:
    short = kachchh_rain(depth_or_period="2016-2025")
    with caplog.at_level(logging.WARNING):
        assert climate_trends([KACHCHH], short, {CHIRPS: dataset(CHIRPS, "2016-2025")}).trends == ()
    assert "at least 30 years" in caplog.text


def test_a_trend_in_other_units_is_not_shown() -> None:
    inches = [
        dataclasses.replace(value, unit="in/year") if value.stat == "NORMAL" else value
        for value in kachchh_rain()
    ]
    assert climate_trends([KACHCHH], inches, {CHIRPS: dataset(CHIRPS)}).trends == ()


def test_significance_is_the_contract_s_threshold() -> None:
    at = [
        dataclasses.replace(v, value=TREND_SIGNIFICANCE) if v.stat == "TREND_P_VALUE" else v
        for v in kachchh_rain()
    ]
    assert climate_trends([KACHCHH], at, {CHIRPS: dataset(CHIRPS)}).trends[0].significant is False


def test_each_trend_variable_reads_its_own_dataset() -> None:
    assert dict(TREND_DATASETS) == {"annual_precipitation": CHIRPS, "annual_mean_temperature": GHCN}
