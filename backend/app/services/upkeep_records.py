from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SourceUpkeep
from app.models.source_upkeep import FETCH_OUTCOMES, PROBLEM_COLUMN_CHARS

__all__ = ["FAILED", "record_archive", "record_archive_try", "record_fetch"]

FAILED = "FAILED"


async def record_fetch(
    session: AsyncSession, source_id: uuid.UUID, *, outcome: str, problem: str | None, now: datetime
) -> None:
    if outcome not in FETCH_OUTCOMES:
        raise ValueError(f"a fetch outcome is one of {', '.join(FETCH_OUTCOMES)}, not {outcome!r}")
    clipped = problem[:PROBLEM_COLUMN_CHARS] if problem else None
    failed = int(outcome == FAILED)
    statement = insert(SourceUpkeep).values(
        sourceId=source_id, checkedAt=now, outcome=outcome, failures=failed, problem=clipped
    )
    failures = SourceUpkeep.__table__.c.failures + 1 if failed else 0
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[SourceUpkeep.sourceId],
            set_={
                "checkedAt": now,
                "outcome": outcome,
                "failures": failures,
                "problem": clipped,
                "updatedAt": now,
            },
        )
    )


async def record_archive_try(session: AsyncSession, source_id: uuid.UUID, *, now: datetime) -> None:
    await session.execute(
        update(SourceUpkeep)
        .where(SourceUpkeep.sourceId == source_id)
        .values(archiveTriedAt=now, updatedAt=now)
    )


async def record_archive(
    session: AsyncSession, source_id: uuid.UUID, snapshot: str, *, now: datetime
) -> None:
    await session.execute(
        update(SourceUpkeep)
        .where(SourceUpkeep.sourceId == source_id)
        .values(archiveTriedAt=now, archivedAt=now, archiveUrl=snapshot, updatedAt=now)
    )
