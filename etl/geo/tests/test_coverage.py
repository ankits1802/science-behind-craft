import pandas as pd

from geo_etl.catalog import MRDS, SOILGRIDS
from geo_etl.coverage import coverage_of
from geo_etl.layers import Result
from geo_etl.rows import Rows

STATE_OF = {11: 1, 12: 1, 21: 2, 31: 3, 32: 3}


def selection() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "districtLgd": list(STATE_OF),
            "stateLgd": list(STATE_OF.values()),
            "districtName": [f"d{lgd}" for lgd in STATE_OF],
        }
    )


def result_with_values(
    lgds: list[int], failures: list[dict] | None = None, without_cells: list[int] | None = None
) -> Result:
    rows = Rows(SOILGRIDS, "fixture")
    frame = selection().set_index("districtLgd", drop=False)
    for lgd in lgds:
        rows.add(frame.loc[lgd], "clay", "0-5cm", "DISTRICT_MEAN", 20.0, "%")
    return Result(SOILGRIDS, rows.frame(), failures=failures or [], districts_without_cells=without_cells or [])


def test_full_coverage_loses_nothing():
    reach = coverage_of(selection(), result_with_values(list(STATE_OF)))
    assert reach.districts_without_values == []
    assert reach.lost_states == []


def test_a_scattered_district_failure_loses_no_state():
    failures = [{"step": "worldcover", "districtLgds": [12], "error": "boom"}]
    reach = coverage_of(selection(), result_with_values([11, 21, 31, 32], failures))
    assert reach.districts_without_values == [12]
    assert reach.lost_states == []


def test_a_state_with_no_values_is_lost_even_without_a_failure():
    reach = coverage_of(selection(), result_with_values([11, 12, 31, 32]))
    assert reach.districts_without_values == [21]
    assert reach.lost_states == [2]


def test_a_step_failed_for_every_district_of_a_state_loses_it_despite_other_values():
    failures = [{"step": "clay 0-5cm Q0.05", "districtLgds": [31, 32], "error": "boom"}]
    reach = coverage_of(selection(), result_with_values(list(STATE_OF), failures))
    assert reach.districts_without_values == []
    assert reach.lost_states == [3]


def test_a_whole_shard_failure_loses_every_state_in_it():
    failures = [{"step": "chelsa bio1 1981-2010", "districtLgds": list(STATE_OF), "error": "Mixed-type"}]
    reach = coverage_of(selection(), result_with_values([], failures))
    assert reach.districts_without_values == [11, 12, 21, 31, 32]
    assert reach.lost_states == [1, 2, 3]


def test_geology_rows_count_as_coverage():
    geology = pd.DataFrame({"districtLgd": [21], "datasetCode": [MRDS.code]})
    result = Result(MRDS, result_with_values([11, 12, 31, 32]).values, geology=geology)
    reach = coverage_of(selection(), result)
    assert reach.districts_without_values == []
    assert reach.lost_states == []


def test_a_one_district_state_without_valid_cells_is_not_lost_and_is_listed():
    reach = coverage_of(selection(), result_with_values([11, 12, 31, 32], without_cells=[21]))
    assert reach.districts_without_values == [21]
    assert reach.districts_without_cells == [21]
    assert reach.lost_states == []


def test_a_state_whose_districts_silently_produced_nothing_is_still_lost():
    reach = coverage_of(selection(), result_with_values([11, 12], without_cells=[21]))
    assert reach.districts_without_values == [21, 31, 32]
    assert reach.districts_without_cells == [21]
    assert reach.lost_states == [3]


def test_a_failure_covering_a_whole_state_loses_it_despite_no_cells_records():
    failures = [{"step": "glim", "districtLgds": [31, 32], "error": "boom"}]
    reach = coverage_of(selection(), result_with_values([11, 12, 21], failures, without_cells=[31, 32]))
    assert reach.districts_without_values == [31, 32]
    assert reach.districts_without_cells == [31, 32]
    assert reach.lost_states == [3]


def test_a_district_without_cells_inside_a_covered_state_is_listed_and_loses_nothing():
    reach = coverage_of(selection(), result_with_values([11, 21, 31, 32], without_cells=[12]))
    assert reach.districts_without_values == [12]
    assert reach.districts_without_cells == [12]
    assert reach.lost_states == []


def test_one_district_without_cells_accounts_for_a_state_whose_other_district_is_silent():
    reach = coverage_of(selection(), result_with_values([11, 12, 21], without_cells=[31]))
    assert reach.districts_without_values == [31, 32]
    assert reach.districts_without_cells == [31]
    assert reach.lost_states == []


def test_a_no_cells_record_is_ignored_for_a_district_with_values_or_outside_the_selection():
    reach = coverage_of(selection(), result_with_values(list(STATE_OF), without_cells=[11, 99]))
    assert reach.districts_without_values == []
    assert reach.districts_without_cells == []
    assert reach.lost_states == []
