from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..records import clean_text
from .wikidata_statements import ENTITY_PREFIX, ITEM_ID, ONTOLOGY_PREFIX, binding_value

__all__ = [
    "COORDINATES_IDS_MAX",
    "PLACE_SEARCH_LIMIT",
    "PlaceCandidate",
    "PlacePoint",
    "coordinates_from_bindings",
    "coordinates_query",
    "exact_candidates",
]

PLACE_SEARCH_LIMIT = 10
COORDINATES_IDS_MAX = 20
EARTH_POINT = re.compile(r"^Point\((-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)\)$")
RANK_ORDER = {"PreferredRank": 0, "NormalRank": 1}
COORDINATES_QUERY = """SELECT ?item ?coordinates ?rank WHERE {
  VALUES ?item { %(items)s }
  ?item p:P625 ?statement .
  ?statement ps:P625 ?coordinates ; wikibase:rank ?rank .
}"""


@dataclass(frozen=True)
class PlaceCandidate:
    item_id: str
    label: str
    description: str | None


@dataclass(frozen=True)
class PlacePoint:
    latitude: float
    longitude: float


def exact_candidates(name: str, hits: Iterable[Mapping[str, Any]]) -> list[PlaceCandidate]:
    wanted = name.strip().casefold()
    found: dict[str, PlaceCandidate] = {}
    for hit in hits:
        item_id = clean_text(hit.get("id")) or ""
        match = hit.get("match") if isinstance(hit.get("match"), Mapping) else {}
        matched = clean_text(match.get("text")) or ""
        label = clean_text(hit.get("label"))
        if ITEM_ID.match(item_id) and label and matched.casefold() == wanted and item_id not in found:
            found[item_id] = PlaceCandidate(item_id, label, clean_text(hit.get("description")))
    return list(found.values())


def coordinates_query(item_ids: Sequence[str]) -> str:
    if not item_ids or len(item_ids) > COORDINATES_IDS_MAX:
        raise ValueError(f"ask for the coordinates of 1 to {COORDINATES_IDS_MAX} items at a time")
    bad = [item_id for item_id in item_ids if not ITEM_ID.match(item_id)]
    if bad:
        raise ValueError(f"{', '.join(bad)} are not Wikidata item ids")
    return COORDINATES_QUERY % {"items": " ".join(f"wd:{item_id}" for item_id in item_ids)}


def coordinates_from_bindings(bindings: Iterable[Mapping[str, Any]]) -> dict[str, PlacePoint]:
    ranked: dict[str, dict[int, set[PlacePoint]]] = {}
    for row in bindings:
        item_id = (binding_value(row, "item") or "").removeprefix(ENTITY_PREFIX)
        rank = RANK_ORDER.get((binding_value(row, "rank") or "").removeprefix(ONTOLOGY_PREFIX))
        point = _earth_point(binding_value(row, "coordinates"))
        if ITEM_ID.match(item_id) and rank is not None and point is not None:
            ranked.setdefault(item_id, {}).setdefault(rank, set()).add(point)
    found: dict[str, PlacePoint] = {}
    for item_id, by_rank in ranked.items():
        best = by_rank[min(by_rank)]
        if len(best) == 1:
            found[item_id] = next(iter(best))
    return found


def _earth_point(literal: str | None) -> PlacePoint | None:
    match = EARTH_POINT.match(literal or "")
    if match is None:
        return None
    longitude, latitude = float(match.group(1)), float(match.group(2))
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return PlacePoint(latitude=latitude, longitude=longitude)
