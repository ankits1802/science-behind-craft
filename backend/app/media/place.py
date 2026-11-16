from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.research.vocabulary import LEVEL_ORDER
from app.services.naming import PlaceParts

__all__ = ["PRECISION_ORDER", "LocationFacts", "media_place"]

PRECISION_ORDER = {"POINT": 0, "DISTRICT": 1, "STATE": 2}
NAMED_PRECISIONS = frozenset({"POINT", "DISTRICT"})


@dataclass(frozen=True)
class LocationFacts:
    id: str
    precision: str
    place_label: str | None
    level: str
    district: str | None
    state: str | None


def media_place(
    locations: Sequence[LocationFacts], practice_states: Sequence[str]
) -> tuple[PlaceParts, tuple[str, ...]]:
    ranked = sorted(
        locations,
        key=lambda found: (
            PRECISION_ORDER.get(found.precision, 9),
            LEVEL_ORDER.get(found.level, 9),
            found.id,
        ),
    )
    names = tuple(
        dict.fromkeys(
            name for found in ranked if found.precision in NAMED_PRECISIONS for name in _names(found)
        )
    )
    if not ranked:
        return PlaceParts(state=practice_states[0] if practice_states else None), names
    best = ranked[0]
    if best.precision in NAMED_PRECISIONS:
        return PlaceParts(locality=best.place_label, district=best.district, state=best.state), names
    return PlaceParts(state=best.state or best.place_label), names


def _names(location: LocationFacts) -> list[str]:
    return [name.strip() for name in (location.place_label, location.district) if name and name.strip()]
