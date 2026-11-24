from __future__ import annotations

import uuid
from datetime import datetime
from types import MappingProxyType
from typing import Any

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import ImageContribution, Process, ProcessCondition, ProcessStage, Reaction, StageReview, User
from app.research.review_labels import cut_label
from app.research.review_queue_stages import PLACED_STATUS, REJECTED_STAGE_STATUS
from app.research.staged_reviews import REMOVE, StagedDecision

from . import audit
from .curation_writes import update_rows
from .open_work_subjects import CATEGORY
from .page_revalidation import craft_owners
from .published_kinds import NO_ITEM, Carried, PublishedKind, PublishedLine, PublishedQuery, PublishedRef

__all__ = ["PUBLISHED_STAGES", "STAGE_REMOVED"]

STAGE_REMOVED = "stage.removed"
REMOVED = (
    "Removed: {name} leaves the process of {process}, the stages after it moving up one, and its facts, "
    "placing and reason stay in the record."
)
HELD = (
    "{name} still holds {held}, which would go with it: remove or move them first, then stage its removal "
    "anew."
)
CRAFT_PAGES = "Stages belong to a craft's process; name the craft whose placed stages to list."


def _placed() -> Select[Any]:
    return (
        select(StageReview, ProcessStage, Process.name, Process.craftId)
        .join(ProcessStage, ProcessStage.id == StageReview.processStageId)
        .join(Process, Process.id == ProcessStage.processId)
        .where(StageReview.status == PLACED_STATUS)
    )


def _named(stage: str, process: str) -> str:
    return cut_label(f"Stage: {stage}, in {process}")


async def _name(session: AsyncSession, ref: PublishedRef) -> str | None:
    found = (await session.execute(_placed().where(StageReview.conceptId == ref.id))).first()
    return None if found is None else _named(found[1].name, found[2])


async def _held(session: AsyncSession, stage_id: uuid.UUID) -> list[str]:
    counts = {
        ("condition", "conditions"): ProcessCondition.stageId == stage_id,
        ("reaction", "reactions"): Reaction.stageId == stage_id,
        ("picture", "pictures"): ImageContribution.stageId == stage_id,
    }
    held = []
    for (one, many), where in counts.items():
        counted = int(await session.scalar(select(func.count()).where(where)) or 0)
        if counted:
            held.append(f"{counted} {one if counted == 1 else many}")
    return held


async def _remove(session: AsyncSession, decision: StagedDecision, reviewer: User, _now: datetime) -> Carried:
    found = (
        await session.execute(
            _placed()
            .where(StageReview.conceptId == decision.id)
            .with_for_update(of=StageReview)
            .execution_options(populate_existing=True)
        )
    ).first()
    if found is None:
        raise InvalidInput(NO_ITEM.format(kind="stage", id=decision.id))
    review, stage, process, craft_id = found
    held = await _held(session, stage.id)
    if held:
        raise InvalidInput(HELD.format(name=stage.name, held=", ".join(held)))
    detail = {"name": stage.name, "process": str(stage.processId), "ordinal": stage.ordinal}
    review.status, review.note, review.reviewerId = REJECTED_STAGE_STATUS, decision.reason, reviewer.id
    review.processStageId = None
    place = (stage.processId, stage.ordinal)
    await session.execute(delete(ProcessStage).where(ProcessStage.id == stage.id))
    await _closed_up(session, place)
    await audit.record(
        session,
        action=STAGE_REMOVED,
        actor=reviewer,
        target_type="Concept",
        target_id=review.conceptId,
        detail={**detail, "reason": decision.reason},
    )
    await session.flush()
    return Carried(REMOVED.format(name=stage.name, process=process), await craft_owners(session, [craft_id]))


async def _closed_up(session: AsyncSession, place: tuple[uuid.UUID, int]) -> None:
    process_id, ordinal = place
    later = await session.execute(
        select(ProcessStage.id, ProcessStage.ordinal).where(
            ProcessStage.processId == process_id, ProcessStage.ordinal > ordinal
        )
    )
    moved = [{"id": stage_id, "ordinal": held - 1} for stage_id, held in later.tuples().all()]
    await update_rows(session, ProcessStage, [{**row, "ordinal": -row["ordinal"] - 1} for row in moved])
    await update_rows(session, ProcessStage, moved)


async def _listed(session: AsyncSession, query: PublishedQuery) -> list[PublishedLine]:
    if query.page is None or query.page.kind == CATEGORY:
        raise InvalidInput(CRAFT_PAGES)
    rows = await session.execute(
        _placed()
        .where(Process.craftId == query.page.id)
        .order_by(Process.name, ProcessStage.ordinal)
        .offset(query.offset)
        .limit(query.limit)
    )
    return [
        PublishedLine(review.conceptId, _named(stage.name, process))
        for review, stage, process, _ in rows.tuples().all()
    ]


PUBLISHED_STAGES = PublishedKind(
    noun="stage", name=_name, actions=MappingProxyType({REMOVE: _remove}), listed=_listed
)
