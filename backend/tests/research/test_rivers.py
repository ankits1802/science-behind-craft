from typing import Any

import pytest
from pydantic import ValidationError

from app.research.rivers import RiverReach, RiverTrace, trace_problems

SOURCE, MIDDLE, TRIBUTARY, MOUTH = 41000010, 41000020, 41000030, 41000040


def reach(hyriv_id: int, next_down: int, **changes: Any) -> RiverReach:
    body = {
        "hyrivId": hyriv_id,
        "nextDown": next_down,
        "mainRiv": MOUTH,
        "ordStra": 2,
        "uplandSkm": 120.5,
        "disAvCms": 0.4,
        "lengthKm": 3.2,
        "geometry": [[69.80, 23.40], [69.81, 23.38]],
    }
    return RiverReach.model_validate(body | changes)


def basin() -> dict[int, RiverReach]:
    return {
        SOURCE: reach(SOURCE, MIDDLE),
        TRIBUTARY: reach(TRIBUTARY, MIDDLE),
        MIDDLE: reach(MIDDLE, MOUTH),
        MOUTH: reach(MOUTH, 0),
    }


def trace(reach_ids: list[int], districts: list[int] | None = None) -> RiverTrace:
    return RiverTrace.model_validate(
        {
            "datasetCode": "HYDRORIVERS_1_0",
            "mainRiv": MOUTH,
            "reachIds": reach_ids,
            "districtLgds": [449] if districts is None else districts,
        }
    )


def test_a_reach_ends_its_river_exactly_at_the_outlet() -> None:
    assert reach(MOUTH, 0).hyriv_id == MOUTH
    with pytest.raises(ValidationError, match="exactly when it is the river's outlet"):
        reach(MIDDLE, 0)
    with pytest.raises(ValidationError, match="exactly when it is the river's outlet"):
        reach(MOUTH, MIDDLE)
    with pytest.raises(ValidationError, match="never flows into itself"):
        reach(MIDDLE, MIDDLE)
    with pytest.raises(ValidationError, match="at least 2"):
        reach(MIDDLE, MOUTH, geometry=[[69.8, 23.4]])
    with pytest.raises(ValidationError, match="less than or equal to 90"):
        reach(MIDDLE, MOUTH, geometry=[[69.8, 23.4], [69.8, 91.0]])


def test_a_trace_runs_from_a_source_to_the_outlet_once_each() -> None:
    assert trace_problems(trace([SOURCE, MIDDLE, MOUTH]), basin()) == []
    with pytest.raises(ValidationError, match="from its source to its outlet"):
        trace([SOURCE, MIDDLE])
    with pytest.raises(ValidationError, match="from its source to its outlet"):
        trace([SOURCE, MIDDLE, SOURCE, MOUTH])
    with pytest.raises(ValidationError, match="each district it reaches once"):
        trace([SOURCE, MIDDLE, MOUTH], [449, 449])


def test_a_trace_follows_next_down_from_a_headwater() -> None:
    assert trace_problems(trace([SOURCE, MOUTH]), basin()) == [
        f"reach {SOURCE} flows into {MIDDLE}, not {MOUTH}"
    ]
    assert trace_problems(trace([MIDDLE, MOUTH]), basin()) == [
        f"reach {MIDDLE} has a reach upstream, so the path does not start at a source"
    ]
    assert trace_problems(trace([99, MIDDLE, MOUTH]), basin()) == ["reach 99 is not stored"]
    other = basin() | {SOURCE: reach(SOURCE, MIDDLE, mainRiv=MIDDLE + 1)}
    assert trace_problems(trace([SOURCE, MIDDLE, MOUTH]), other) == [
        f"reach {SOURCE} belongs to river {MIDDLE + 1}, not {MOUTH}"
    ]
