from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import Any

from .craft_master_loader import DATA_DIR

__all__ = ["REGISTER_FILE", "DistrictRegister", "load_district_register", "parse_district_register"]

REGISTER_FILE = DATA_DIR / "lgd_register.json"


@dataclass(frozen=True)
class DistrictRegister:
    states: frozenset[str]
    districts: Mapping[str, frozenset[str]]

    def has_state(self, name: str) -> bool:
        return name in self.states

    def has_district(self, state: str, name: str) -> bool:
        return name in self.districts.get(state, frozenset())

    def district_names(self, state: str) -> frozenset[str]:
        return self.districts.get(state, frozenset())

    def place_names(self) -> frozenset[str]:
        return self.states.union(*self.districts.values())


def parse_district_register(raw: Mapping[str, Any]) -> DistrictRegister:
    state_names = {int(row["lgd"]): str(row["name"]) for row in raw["states"]}
    named: dict[str, set[str]] = {name: set() for name in state_names.values()}
    for row in raw["districts"]:
        state_lgd = int(row["stateLgd"])
        if state_lgd not in state_names:
            raise ValueError(
                f"district {row['lgd']} names state {state_lgd}, which the register does not list"
            )
        named[state_names[state_lgd]].add(str(row["name"]))
    for row in raw.get("pending", []):
        if row["state"] not in named:
            raise ValueError(f"pending district {row['district']} names unknown state {row['state']}")
        named[row["state"]].add(str(row["district"]))
    return DistrictRegister(
        states=frozenset(named),
        districts=MappingProxyType({state: frozenset(names) for state, names in named.items()}),
    )


@lru_cache(maxsize=1)
def load_district_register() -> DistrictRegister:
    return parse_district_register(json.loads(REGISTER_FILE.read_text(encoding="utf-8")))
