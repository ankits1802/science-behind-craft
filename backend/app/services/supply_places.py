from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from typing import Protocol

from app.research.blocks import stated_texts
from app.research.blocks_place import SupplyLink
from app.sources.reference.wikidata_places import PlaceCandidate, PlacePoint

from .supply_links import OriginPlace

__all__ = [
    "PLACED_ORIGINS_MAX",
    "PlaceFinder",
    "chosen_candidate",
    "context_words",
    "origin_places",
]

PLACED_ORIGINS_MAX = 8
CONTEXT_WORD = re.compile(r"\b[A-Z][\w-]{3,}")
DESCRIPTION_WORD = re.compile(r"[\w-]+")


class PlaceFinder(Protocol):
    async def place_candidates(self, name: str) -> list[PlaceCandidate]: ...

    async def place_points(self, item_ids: Sequence[str]) -> dict[str, PlacePoint]: ...


async def origin_places(finder: PlaceFinder, links: Sequence[SupplyLink]) -> dict[str, OriginPlace]:
    chosen: dict[str, str] = {}
    for key, (origin, words) in list(_origin_contexts(links).items())[:PLACED_ORIGINS_MAX]:
        candidate = chosen_candidate(await finder.place_candidates(origin), words)
        if candidate is not None:
            chosen[key] = candidate.item_id
    if not chosen:
        return {}
    points = await finder.place_points(list(dict.fromkeys(chosen.values())))
    return {
        key: OriginPlace(item_id, points[item_id].latitude, points[item_id].longitude)
        for key, item_id in chosen.items()
        if item_id in points
    }


def chosen_candidate(candidates: Sequence[PlaceCandidate], words: Collection[str]) -> PlaceCandidate | None:
    if len(candidates) == 1:
        return candidates[0]
    described = [
        candidate
        for candidate in candidates
        if candidate.description and set(DESCRIPTION_WORD.findall(candidate.description)) & set(words)
    ]
    return described[0] if len(described) == 1 else None


def context_words(link: SupplyLink) -> frozenset[str]:
    own = {*DESCRIPTION_WORD.findall(link.origin), *DESCRIPTION_WORD.findall(link.material)}
    stated = {word for text in stated_texts(link.sentence) for word in CONTEXT_WORD.findall(text)}
    return frozenset(stated - own)


def _origin_contexts(links: Sequence[SupplyLink]) -> dict[str, tuple[str, frozenset[str]]]:
    found: dict[str, tuple[str, frozenset[str]]] = {}
    for link in links:
        key = link.origin.casefold()
        origin, words = found.get(key, (link.origin, frozenset()))
        found[key] = (origin, words | context_words(link))
    return found
