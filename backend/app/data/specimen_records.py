from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from types import MappingProxyType
from typing import Any

from .contributor_kit import design_tokens

__all__ = ["SpecimenRecord", "craft_specimens", "specimen_records", "stated_specimens"]

SPECIMEN_GROUP = "specimen"
MATERIAL_KEY = "material"


@dataclass(frozen=True)
class SpecimenRecord:
    token: str
    craft: str
    material: str
    claims: tuple[str, ...]


@cache
def specimen_records() -> tuple[SpecimenRecord, ...]:
    tokens: dict[str, Any] = json.loads(design_tokens())[SPECIMEN_GROUP]
    return tuple(
        SpecimenRecord(
            token=str(entry["cssVar"]),
            craft=str(entry[MATERIAL_KEY]["craft"]),
            material=str(entry[MATERIAL_KEY]["material"]),
            claims=tuple(str(claim) for claim in entry[MATERIAL_KEY].get("claims") or ()),
        )
        for entry in tokens.values()
        if isinstance(entry, dict) and isinstance(entry.get(MATERIAL_KEY), dict)
    )


def craft_specimens(craft_slug: str) -> Mapping[str, tuple[str, ...]]:
    return _grouped(craft_slug, lambda record: (record.material,))


def stated_specimens(craft_slug: str) -> Mapping[str, tuple[str, ...]]:
    return _grouped(craft_slug, lambda record: record.claims)


def _grouped(
    craft_slug: str, keys: Callable[[SpecimenRecord], Iterable[str]]
) -> Mapping[str, tuple[str, ...]]:
    found: dict[str, list[str]] = {}
    for record in specimen_records():
        if record.craft == craft_slug:
            for key in keys(record):
                found.setdefault(key, []).append(record.token)
    return MappingProxyType({key: tuple(tokens) for key, tokens in found.items()})
