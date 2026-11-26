from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.data.district_register import DistrictCodes
from app.data.river_aliases import RiverAlias
from app.data.river_names import name_forms

__all__ = [
    "CHECK_SUFFIX",
    "DOSSIERS",
    "RIVER_NAMES",
    "RIVER_PLACE",
    "Register",
    "RegisterRiver",
    "accepted_names",
    "alias_rivers",
    "dossier_rivers",
    "named_rivers",
    "register_of",
    "site_register",
]

RIVER_PLACE = "RIVER"
RIVER_NAMES = Path("backend/app/data/rivers")
DOSSIERS = (Path("backend/app/data/curation"), Path("backend/app/data/curation/categories"))
CHECK_SUFFIX = ".check.json"


@dataclass(frozen=True)
class RegisterRiver:
    name: str
    districts: frozenset[int]
    source: str
    also: tuple[str, ...] = ()

    @property
    def names(self) -> tuple[str, ...]:
        return (self.name, *self.also)


@dataclass(frozen=True)
class Register:
    by_form: Mapping[str, tuple[RegisterRiver, ...]]

    def agreeing(self, name: str, districts: Iterable[int]) -> list[RegisterRiver]:
        crossed = set(districts)
        found = {river for form in _forms(name) for river in self.by_form.get(form, ())}
        return sorted(
            (river for river in found if crossed & river.districts),
            key=lambda river: (river.name, river.source),
        )


def _forms(name: str) -> set[str]:
    return {form.casefold() for form in name_forms(name)}


def register_of(rivers: Iterable[RegisterRiver]) -> Register:
    by_form: dict[str, list[RegisterRiver]] = defaultdict(list)
    for river in rivers:
        for form in sorted({form for name in river.names for form in _forms(name)}):
            by_form[form].append(river)
    return Register({form: tuple(found) for form, found in by_form.items()})


def site_register(root: Path, codes: DistrictCodes, aliases: Iterable[RiverAlias]) -> Register:
    dossiers = [
        path
        for folder in DOSSIERS
        for path in sorted((root / folder).glob("*.json"))
        if not path.name.endswith(CHECK_SUFFIX)
    ]
    return register_of(
        [
            *named_rivers(sorted((root / RIVER_NAMES).glob("river_names.*.json"))),
            *dossier_rivers(dossiers, codes),
            *alias_rivers(aliases),
        ]
    )


def named_rivers(files: Iterable[Path]) -> list[RegisterRiver]:
    rivers: list[RegisterRiver] = []
    for path in files:
        body = json.loads(path.read_text(encoding="utf-8"))
        code = str(body["dataset"]["code"])
        rivers += [
            RegisterRiver(str(row["name"]), frozenset(int(lgd) for lgd in row["districtLgds"]), code)
            for row in body["rivers"]
        ]
    return rivers


def dossier_rivers(dossiers: Iterable[Path], codes: DistrictCodes) -> list[RegisterRiver]:
    rivers: list[RegisterRiver] = []
    for path in dossiers:
        body = json.loads(path.read_text(encoding="utf-8"))
        slug = str(body.get("craftSlug") or body.get("categorySlug") or path.stem)
        places = [place for place in body.get("places", []) if place.get("kind") == RIVER_PLACE]
        rivers += [river for place in places if (river := _dossier_river(place, codes, slug))]
    return rivers


def _dossier_river(place: Mapping[str, Any], codes: DistrictCodes, slug: str) -> RegisterRiver | None:
    state, district = place.get("state"), place.get("district")
    lgd = codes.district_lgd(str(state), str(district)) if state and district else None
    return RegisterRiver(str(place["name"]), frozenset({lgd}), slug) if lgd is not None else None


def alias_rivers(aliases: Iterable[RiverAlias]) -> list[RegisterRiver]:
    return [
        RegisterRiver(alias.names[0], alias.district_lgds, alias.ref, alias.names[1:]) for alias in aliases
    ]


def accepted_names(name: str, agreed: Iterable[RegisterRiver]) -> list[str]:
    names = [name, *name_forms(name)]
    for river in agreed:
        names += [form for held in river.names for form in (held, *name_forms(held))]
    return sorted(set(names))
