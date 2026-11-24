from __future__ import annotations

from datetime import datetime
from types import MappingProxyType
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import ConditionReading, Process, ProcessCondition, ProcessStage, Reaction, User
from app.models.science import READING_REJECTED, live_process, shown_reading
from app.research.review_labels import cut_label
from app.research.staged_reviews import REMOVE, StagedDecision

from . import audit
from .open_work_subjects import CATEGORY
from .page_revalidation import craft_owners
from .published_kinds import NO_ITEM, Carried, PublishedKind, PublishedLine, PublishedQuery, PublishedRef

__all__ = ["PUBLISHED_READINGS", "READING_REMOVED"]

READING_REMOVED = "reading.removed"
REMOVED = (
    "Removed: the reading leaves the process view and the craft's pages, and the row and its reason are kept."
)
CRAFT_PAGES = "Readings belong to a craft's process; name the craft whose readings to list."


def _readings() -> Select[Any]:
    return (
        select(ConditionReading, ProcessCondition.label, ProcessStage.name, Process.craftId)
        .join(ProcessCondition, ProcessCondition.id == ConditionReading.conditionId)
        .outerjoin(Reaction, Reaction.id == ProcessCondition.reactionId)
        .join(ProcessStage, ProcessStage.id == func.coalesce(ProcessCondition.stageId, Reaction.stageId))
        .join(Process, Process.id == ProcessStage.processId)
        .where(shown_reading(), live_process())
    )


def _named(condition: str, stated: str, stage: str) -> str:
    return cut_label(f"Reading: {condition} {stated}, {stage}")


async def _name(session: AsyncSession, ref: PublishedRef) -> str | None:
    found = (await session.execute(_readings().where(ConditionReading.id == ref.id))).first()
    return None if found is None else _named(found[1], found[0].stated, found[2])


async def _remove(session: AsyncSession, decision: StagedDecision, reviewer: User, now: datetime) -> Carried:
    found = (await session.execute(_readings().where(ConditionReading.id == decision.id))).first()
    row = await session.get(ConditionReading, decision.id, with_for_update=True, populate_existing=True)
    if found is None or row is None or row.reviewStatus == READING_REJECTED:
        raise InvalidInput(NO_ITEM.format(kind="reading", id=decision.id))
    was = row.reviewStatus
    row.reviewStatus, row.reviewedById, row.reviewedAt, row.reviewNote = (
        READING_REJECTED,
        reviewer.id,
        now,
        decision.reason,
    )
    await audit.record(
        session,
        action=READING_REMOVED,
        actor=reviewer,
        target_type="ConditionReading",
        target_id=row.id,
        detail={"from": was, "stated": row.stated, "reason": decision.reason},
    )
    await session.flush()
    return Carried(REMOVED, await craft_owners(session, [found[3]]))


async def _listed(session: AsyncSession, query: PublishedQuery) -> list[PublishedLine]:
    if query.page is None or query.page.kind == CATEGORY:
        raise InvalidInput(CRAFT_PAGES)
    rows = await session.execute(
        _readings()
        .where(Process.craftId == query.page.id)
        .order_by(ConditionReading.createdAt, ConditionReading.id)
        .offset(query.offset)
        .limit(query.limit)
    )
    return [
        PublishedLine(row.id, _named(label, row.stated, stage))
        for row, label, stage, _ in rows.tuples().all()
    ]


PUBLISHED_READINGS = PublishedKind(
    noun="reading", name=_name, actions=MappingProxyType({REMOVE: _remove}), listed=_listed
)
