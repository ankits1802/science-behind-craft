from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ExternalFailure

from .place_lookups import StoredPlaces
from .source_lookup_models import EntityLookup
from .supply_places import PlaceFinder

__all__ = ["entity_points"]

logger = logging.getLogger(__name__)


async def entity_points(
    found: EntityLookup, finder: PlaceFinder, sessions: async_sessionmaker[AsyncSession]
) -> EntityLookup:
    if not found.entities:
        return found

    async def live() -> PlaceFinder:
        return finder

    try:
        points = await StoredPlaces(sessions, live).place_points([entity.qid for entity in found.entities])
    except ExternalFailure as failure:
        logger.warning("the looked-up items are shown without their points: %s", failure)
        return found
    entities = [
        entity.model_copy(update={"latitude": point.latitude, "longitude": point.longitude})
        if (point := points.get(entity.qid)) is not None
        else entity
        for entity in found.entities
    ]
    return found.model_copy(update={"entities": entities})
