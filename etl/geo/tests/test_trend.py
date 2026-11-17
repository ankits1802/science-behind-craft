import math

import pandas as pd
import pytest

from geo_etl.catalog import CHIRPS
from geo_etl.rows import Rows
from geo_etl.trend import AnnualSeries, add_trend_rows, mann_kendall_p, sen_slope, series_trend

KACHCHH = pd.Series({"districtLgd": 449, "stateLgd": 24, "districtName": "Kachchh"})


def test_the_sen_slope_is_the_median_of_the_pairwise_slopes():
    assert sen_slope([3.0, 1.0, 4.0, 1.0, 5.0]) == pytest.approx(0.5)


def test_the_mann_kendall_p_value_corrects_for_ties_and_continuity():
    assert mann_kendall_p([3.0, 1.0, 4.0, 1.0, 5.0]) == pytest.approx(0.613354, abs=2e-6)


def test_a_flat_series_has_no_trend():
    assert sen_slope([7.0] * 4) == 0.0
    assert mann_kendall_p([7.0] * 4) == 1.0


def test_a_steady_rise_over_thirty_years_is_significant():
    series = AnnualSeries("annual_precipitation", 1996, tuple(400.0 + 2.0 * k for k in range(30)))
    trend = series_trend(series)
    assert series.period == "1996-2025"
    assert trend.slope_per_decade == pytest.approx(20.0)
    assert trend.p_value == pytest.approx(math.erfc(434 / math.sqrt(56550 / 18) / math.sqrt(2)))
    assert trend.p_value < 1e-12


def test_no_trend_is_given_for_a_short_or_broken_series():
    steady = tuple(400.0 + k for k in range(30))
    assert series_trend(AnnualSeries("annual_precipitation", 1997, steady[1:])) is None
    broken = (*steady[:10], math.nan, *steady[11:])
    assert series_trend(AnnualSeries("annual_precipitation", 1996, broken)) is None


def test_trend_rows_carry_the_variable_s_units_over_the_series_period():
    rows = Rows(CHIRPS, "fake")
    series = AnnualSeries("annual_precipitation", 1996, tuple(400.0 + 2.0 * k for k in range(30)))
    add_trend_rows(rows, KACHCHH, series)
    frame = rows.frame().set_index("stat")
    assert list(frame.index) == ["TREND_PER_DECADE", "TREND_P_VALUE"]
    assert set(frame["depthOrPeriod"]) == {"1996-2025"}
    assert frame.loc["TREND_PER_DECADE", "unit"] == "mm/year per decade"
    assert frame.loc["TREND_PER_DECADE", "value"] == pytest.approx(20.0)
    assert frame.loc["TREND_P_VALUE", "unit"] == "p-value"
    assert "Theil-Sen" in frame.loc["TREND_PER_DECADE", "method"]
