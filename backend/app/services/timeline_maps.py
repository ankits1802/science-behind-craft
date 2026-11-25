from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cache
from types import MappingProxyType
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.map_layers import LAYERS_DIR, MINERALS_FILE, RELIEF_FILE, RIVERS_FILE
from app.geo.datasets import region_dataset
from app.research.component_specs_map_parts import MapParts
from app.research.component_specs_timeline_map import DeclaredTimelineMapSpec
from app.research.datasets import BOUNDARY_CAPTION, BOUNDARY_DATASET_CODE, DatasetRef

from .map_layer_places import held_map_problems
from .map_layer_store import listed_layers
from .region_records import dataset_records
from .supply_places import PlaceFinder
from .timeline_map_places import found_places

__all__ = [
    "NOT_HELD",
    "NO_BOUNDARY",
    "NO_RECORD",
    "PHYSICAL_FILES",
    "MapCredits",
    "SpecPlacement",
    "map_credits",
    "placed_spec",
]

PHYSICAL_FILES = MappingProxyType({"relief": RELIEF_FILE, "rivers": RIVERS_FILE, "minerals": MINERALS_FILE})
NO_BOUNDARY = f"the site holds no {BOUNDARY_DATASET_CODE} record to cite beneath the map"
NOT_HELD = "the site holds no layer named {name!r}: name relief, rivers, minerals or one of its district layers ({held})"
NO_RECORD = "the layer {name} rests on {code}, which the site holds no dataset record for"


@dataclass(frozen=True)
class MapCredits:
    datasets: list[DatasetRef] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SpecPlacement:
    problems: list[str] = field(default_factory=list)
    spec: dict[str, Any] | None = None


async def placed_spec(
    session: AsyncSession, checked: Any, *, finder: PlaceFinder | None = None
) -> SpecPlacement:
    if isinstance(checked, MapParts):
        return SpecPlacement(problems=held_map_problems(checked))
    if not isinstance(checked, DeclaredTimelineMapSpec):
        return SpecPlacement()
    found = await found_places(session, checked, finder=finder)
    credits = await map_credits(session, checked.layers)
    problems = [*found.problems, *credits.problems]
    if problems:
        return SpecPlacement(problems=problems)
    places = [place.model_copy(update={"found": found.places[at]}) for at, place in enumerate(checked.places)]
    parts = {"places": places, "datasets": credits.datasets, "boundary_caption": BOUNDARY_CAPTION}
    placed = checked.model_copy(update=parts)
    return SpecPlacement(spec=placed.model_dump(mode="json"))


async def map_credits(session: AsyncSession, layers: Sequence[str]) -> MapCredits:
    listing = await listed_layers(session)
    boundary = listing.boundary
    if boundary is None:
        return MapCredits(problems=[NO_BOUNDARY])
    held = {layer.spec.id: layer.spec.dataset_code for layer in listing.layers}
    wanted: dict[str, str] = {}
    problems: list[str] = []
    for name in layers:
        codes = physical_codes(name) if name in PHYSICAL_FILES else (held[name],) if name in held else ()
        if not codes:
            problems.append(
                NOT_HELD.format(name=name, held=", ".join(sorted(held)) or "no district layer is stored")
            )
        wanted |= dict.fromkeys(codes, name)
    records = await dataset_records(session, wanted)
    problems += [
        NO_RECORD.format(name=name, code=code) for code, name in wanted.items() if code not in records
    ]
    datasets = [
        region_dataset(boundary),
        *(region_dataset(records[code]) for code in wanted if code in records),
    ]
    return MapCredits(datasets=datasets, problems=problems)


@cache
def physical_codes(name: str) -> tuple[str, ...]:
    body = json.loads((LAYERS_DIR / PHYSICAL_FILES[name]).read_text(encoding="utf-8"))
    rows = body.get("datasets") or [body.get("source") or {}]
    return tuple(dict.fromkeys(str(row["code"]) for row in rows if row.get("code")))
