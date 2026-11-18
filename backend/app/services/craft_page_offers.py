from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.geo.records import PlaceRecord
from app.models import Craft

from .region_records import craft_places
from .shared_concepts import craft_shared_science

__all__ = ["PageOffers", "page_offers", "place_offers"]


@dataclass(frozen=True)
class PageOffers:
    region: bool = False
    region_sources: bool = False
    shared_science: bool = False


def place_offers(places: Sequence[PlaceRecord], *, shared_science: bool) -> PageOffers:
    return PageOffers(
        region=bool(places),
        region_sources=any(place.source_id for place in places),
        shared_science=shared_science,
    )


async def page_offers(session: AsyncSession, craft: Craft) -> PageOffers:
    science = await craft_shared_science(session, craft)
    return place_offers(await craft_places(session, craft), shared_science=bool(science.nodes))
