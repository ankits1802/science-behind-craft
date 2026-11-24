from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminDistrict, PlaceLookup, WikidataPoint
from app.research.component_specs_timeline_map import DeclaredTimelineMapSpec, FoundPlace, TimelineMapPlace
from app.research.map_layer_proposals import POINT_DECIMALS
from app.sources.reference.wikidata_places import PlacePoint

from .place_lookups import item_key
from .supply_places import PlaceFinder

__all__ = ["NOT_IN_REGISTER", "NOT_LOOKED_UP", "OUTSIDE_DISTRICTS", "FoundPlaces", "found_places"]

WGS84 = 4326
NOT_IN_REGISTER = "place {at} names district {lgd}, which the district register holds no point for"
NOT_LOOKED_UP = (
    "place {at} names {item}, which the site holds no point for: look it up with lookup (kind entity, "
    "qid {item}) and deliver it again"
)
OUTSIDE_DISTRICTS = "place {at} is the page's own place, so it lies inside one of India's districts"


@dataclass(frozen=True)
class FoundPlaces:
    places: dict[int, FoundPlace] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


async def found_places(
    session: AsyncSession, spec: DeclaredTimelineMapSpec, *, finder: PlaceFinder | None = None
) -> FoundPlaces:
    districts = await _district_points(session, [p.district for p in spec.places if p.district is not None])
    items = await _item_points(session, [p.wikidata for p in spec.places if p.wikidata is not None], finder)
    found = FoundPlaces()
    for at, place in enumerate(spec.places):
        point = _point(place, districts, items)
        if point is None:
            found.problems.append(_unresolved(at, place))
            continue
        lgd = place.district if place.district is not None else await _district_at(session, point)
        if place.home and lgd is None:
            found.problems.append(OUTSIDE_DISTRICTS.format(at=at))
            continue
        found.places[at] = FoundPlace(
            latitude=round(point.latitude, POINT_DECIMALS),
            longitude=round(point.longitude, POINT_DECIMALS),
            wikidata_id=place.wikidata,
            district_lgd=lgd,
        )
    return found


def _point(
    place: TimelineMapPlace, districts: Mapping[int, PlacePoint], items: Mapping[str, PlacePoint]
) -> PlacePoint | None:
    if place.district is not None:
        return districts.get(place.district)
    if place.wikidata is not None:
        return items.get(place.wikidata)
    if place.latitude is None or place.longitude is None:
        return None
    return PlacePoint(latitude=place.latitude, longitude=place.longitude)


def _unresolved(at: int, place: TimelineMapPlace) -> str:
    if place.district is not None:
        return NOT_IN_REGISTER.format(at=at, lgd=place.district)
    return NOT_LOOKED_UP.format(at=at, item=place.wikidata)


async def _district_points(session: AsyncSession, codes: Collection[int]) -> dict[int, PlacePoint]:
    if not codes:
        return {}
    rows = await session.execute(
        select(AdminDistrict.lgd, func.ST_Y(AdminDistrict.centroid), func.ST_X(AdminDistrict.centroid)).where(
            AdminDistrict.lgd.in_(set(codes)), AdminDistrict.centroid.is_not(None)
        )
    )
    return {
        int(lgd): PlacePoint(float(latitude), float(longitude)) for lgd, latitude, longitude in rows.all()
    }


async def _item_points(
    session: AsyncSession, item_ids: Collection[str], finder: PlaceFinder | None
) -> dict[str, PlacePoint]:
    if not item_ids:
        return {}
    kept = await session.execute(
        select(WikidataPoint.wikidataId, WikidataPoint.latitude, WikidataPoint.longitude).where(
            WikidataPoint.wikidataId.in_(set(item_ids))
        )
    )
    points = {str(item): PlacePoint(float(lat), float(lon)) for item, lat, lon in kept.all()}
    points |= await _looked_up(session, [item for item in item_ids if item not in points])
    asked = [item for item in item_ids if item not in points]
    if asked and finder is not None:
        points |= await finder.place_points(asked)
    return points


async def _looked_up(session: AsyncSession, item_ids: Collection[str]) -> dict[str, PlacePoint]:
    if not item_ids:
        return {}
    keys = {item_key(item): item for item in item_ids}
    rows = await session.execute(
        select(PlaceLookup.lookupKey, PlaceLookup.answer).where(PlaceLookup.lookupKey.in_(list(keys)))
    )
    found: dict[str, PlacePoint] = {}
    for key, answer in rows.tuples().all():
        latitude, longitude = answer.get("latitude"), answer.get("longitude")
        if latitude is not None and longitude is not None:
            found[keys[key]] = PlacePoint(float(latitude), float(longitude))
    return found


async def _district_at(session: AsyncSession, point: PlacePoint) -> int | None:
    located = func.ST_SetSRID(func.ST_MakePoint(point.longitude, point.latitude), WGS84)
    rows = await session.scalars(
        select(AdminDistrict.lgd).where(func.ST_Contains(AdminDistrict.geom, located)).limit(2)
    )
    found = list(rows.all())
    return int(found[0]) if len(found) == 1 else None
