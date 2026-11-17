from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import INDIA_TZ
from app.models import EnvDataset, Source
from app.research.citation_formats import CitedThing, dataset_access_key
from app.research.citations import SourceRef

from .visible_claims import stored_uuids

__all__ = ["accessed_dates"]


async def accessed_dates(session: AsyncSession, cited: Sequence[CitedThing]) -> dict[str, date]:
    source_ids = stored_uuids(thing.id for thing in cited if isinstance(thing, SourceRef))
    codes = [thing.code for thing in cited if not isinstance(thing, SourceRef)]
    found: dict[str, date] = {}
    if source_ids:
        rows = await session.execute(
            select(Source.id, Source.retrievedAt).where(
                Source.id.in_(source_ids), Source.retrievedAt.is_not(None)
            )
        )
        found |= {str(source_id): _day(retrieved) for source_id, retrieved in rows.tuples().all()}
    if codes:
        rows = await session.execute(
            select(EnvDataset.code, EnvDataset.retrievedAt).where(
                EnvDataset.code.in_(codes), EnvDataset.retrievedAt.is_not(None)
            )
        )
        found |= {dataset_access_key(code): _day(retrieved) for code, retrieved in rows.tuples().all()}
    return found


def _day(moment: datetime) -> date:
    return moment.astimezone(INDIA_TZ).date()
