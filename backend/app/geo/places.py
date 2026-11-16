from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence

from app.geo.records import LocationRecord, PlaceRecord, StateRecord
from app.research.vocabulary import LEVEL_ORDER
from app.schemas.region import MASTER_LIST_LABEL

__all__ = [
    "DISTRICT_PRECISIONS",
    "MASTER_LIST_LEVEL",
    "NATIONWIDE",
    "practice_states",
    "region_places",
]

logger = logging.getLogger(__name__)

DISTRICT_PRECISIONS = ("DISTRICT", "POINT")
STATE_PRECISION = "STATE"
MASTER_LIST_LEVEL = "REVIEWED"
NATIONWIDE = "All India"


def practice_states(names: Iterable[str], known: Mapping[str, StateRecord]) -> tuple[StateRecord, ...]:
    found: dict[int, StateRecord] = {}
    for name in names:
        state = known.get(name.strip().casefold())
        if state is not None:
            found.setdefault(state.lgd, state)
        elif name.strip() != NATIONWIDE:
            logger.warning("state of practice %r is not an LGD state", name)
    return tuple(found.values())


def region_places(
    locations: Sequence[LocationRecord], practice: Sequence[StateRecord]
) -> tuple[PlaceRecord, ...]:
    districts: dict[int | None, PlaceRecord] = {}
    cited_states: list[PlaceRecord] = []
    for location in sorted(locations, key=_strongest_first):
        state = _shown_state(location)
        if state is None:
            continue
        if location.precision == STATE_PRECISION:
            cited_states.append(_cited_place(location, state, scope="STATE"))
        else:
            districts.setdefault(location.district_lgd, _cited_place(location, state, scope="DISTRICT"))
    placed = {place.state.lgd for place in districts.values()}
    states = _state_places([*cited_states, *map(_master_list_place, practice)], placed)
    return (*sorted(districts.values(), key=_district_order), *sorted(states, key=_state_order))


def _shown_state(location: LocationRecord) -> StateRecord | None:
    if location.source_id is None or location.source_title is None:
        logger.warning("craft location %s has no visible source and is not shown", location.id)
        return None
    if location.state is None:
        logger.warning("craft location %s names no state and is not shown", location.id)
        return None
    if location.precision in DISTRICT_PRECISIONS and location.district_lgd is None:
        logger.warning("craft location %s lies in no district and is not shown", location.id)
        return None
    return location.state


def _strongest_first(location: LocationRecord) -> tuple[int, str]:
    return LEVEL_ORDER.get(location.level, len(LEVEL_ORDER)), location.id


def _cited_place(location: LocationRecord, state: StateRecord, *, scope: str) -> PlaceRecord:
    district = scope == "DISTRICT"
    return PlaceRecord(
        scope=scope,
        state=state,
        district_lgd=location.district_lgd if district else None,
        district_name=location.district_name if district else None,
        has_polygon=location.has_polygon if district else False,
        place_label=location.place_label or (location.district_name if district else None) or state.name,
        basis_kind="CRAFT_LOCATION",
        source_id=location.source_id,
        basis_label=str(location.source_title),
        level=location.level,
    )


def _state_places(candidates: Sequence[PlaceRecord], placed: set[int]) -> list[PlaceRecord]:
    chosen: dict[int, PlaceRecord] = {}
    for place in sorted(candidates, key=_strongest_basis):
        if place.state.lgd not in placed:
            chosen.setdefault(place.state.lgd, place)
    return list(chosen.values())


def _master_list_place(state: StateRecord) -> PlaceRecord:
    return PlaceRecord(
        scope="STATE",
        state=state,
        district_lgd=None,
        district_name=None,
        has_polygon=False,
        place_label=state.name,
        basis_kind="MASTER_LIST",
        source_id=None,
        basis_label=MASTER_LIST_LABEL,
        level=MASTER_LIST_LEVEL,
    )


def _strongest_basis(place: PlaceRecord) -> tuple[int, int, str]:
    return (
        LEVEL_ORDER.get(place.level, len(LEVEL_ORDER)),
        0 if place.basis_kind == "CRAFT_LOCATION" else 1,
        place.source_id or "",
    )


def _district_order(place: PlaceRecord) -> tuple[str, str, int]:
    return place.state.name.casefold(), (place.district_name or "").casefold(), place.district_lgd or 0


def _state_order(place: PlaceRecord) -> tuple[str, int]:
    return place.state.name.casefold(), place.state.lgd
