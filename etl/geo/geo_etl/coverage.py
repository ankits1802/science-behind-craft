from dataclasses import dataclass

import pandas as pd

from geo_etl.layers import Result

__all__ = ["Coverage", "coverage_of"]


@dataclass(frozen=True)
class Coverage:
    districts_without_values: list[int]
    lost_states: list[int]


def coverage_of(districts: pd.DataFrame, result: Result) -> Coverage:
    members = state_members(districts)
    covered = covered_districts(result)
    lost = {state for state, lgds in members.items() if not lgds & covered}
    for item in result.failures:
        failed = {int(v) for v in item["districtLgds"]}
        lost |= {state for state, lgds in members.items() if lgds <= failed}
    selected = set().union(*members.values()) if members else set()
    return Coverage(districts_without_values=sorted(selected - covered), lost_states=sorted(lost))


def state_members(districts: pd.DataFrame) -> dict[int, set[int]]:
    members: dict[int, set[int]] = {}
    for lgd, state in zip(districts["districtLgd"], districts["stateLgd"], strict=True):
        members.setdefault(int(state), set()).add(int(lgd))
    return members


def covered_districts(result: Result) -> set[int]:
    covered = {int(v) for v in result.values["districtLgd"]}
    if result.geology is not None:
        covered |= {int(v) for v in result.geology["districtLgd"]}
    return covered
