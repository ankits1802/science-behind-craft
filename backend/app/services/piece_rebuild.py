from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, spend_refusal
from app.core.logging import request_id_scope
from app.models import Answer, Craft, KnowledgePiece as PieceRow, User
from app.research.crafts import CraftRef
from app.research.planning import withheld_name
from app.research.understanding import Understanding
from app.research.vocabulary import CANONICAL_LANGUAGE

from .answering import AnswerAsk, AnswerPipeline, answer_understood
from .coverage_enrichment import ENRICHMENT_QUESTION_RESERVE_USD, ENRICHMENT_TAG

__all__ = [
    "PIECE_REBUILD_ASK_WINDOW",
    "PIECE_REBUILD_CRAFTS",
    "PIECE_REBUILD_TAG",
    "PieceRebuildReport",
    "RebuildOutcome",
    "StaleGroup",
    "rebuild_group",
    "rebuild_understanding",
    "run_piece_rebuild",
    "stale_groups",
]

logger = logging.getLogger(__name__)

PIECE_REBUILD_ASK_WINDOW = timedelta(days=30)
PIECE_REBUILD_CRAFTS = 10
PIECE_REBUILD_TAG = f"{ENRICHMENT_TAG}rebuild-"
BUDGET_STOP = "BUDGET"
SPEND_STOP = "SPEND_REFUSED"
REBUILT = "REBUILT"
EMPTY = "EMPTY"


@dataclass(frozen=True)
class StaleGroup:
    craft: CraftRef
    facet: str
    depth: str
    question: str
    asks: int
    seats: tuple[str, ...] = ()
    withheld_terms: tuple[str, ...] = ()


@dataclass
class RebuildOutcome:
    craft: str
    facet: str
    depth: str
    status: str
    error: str | None = None


@dataclass
class PieceRebuildReport:
    budget_usd: str
    groups: list[RebuildOutcome] = field(default_factory=list)
    stopped: str | None = None

    @property
    def ok(self) -> bool:
        return all(group.status != "FAILED" for group in self.groups)

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "ok": self.ok}


Rebuild = Callable[[StaleGroup], Awaitable[str]]
Remaining = Callable[[], Awaitable[Decimal]]


async def stale_groups(
    session: AsyncSession, *, now: datetime, crafts: int = PIECE_REBUILD_CRAFTS
) -> list[StaleGroup]:
    asks = (
        select(Answer.craftId.label("craftId"), func.count().label("asks"))
        .where(Answer.userId.is_not(None), Answer.craftId.is_not(None))
        .where(Answer.createdAt >= now - PIECE_REBUILD_ASK_WINDOW)
        .group_by(Answer.craftId)
        .order_by(func.count().desc(), Answer.craftId)
        .limit(crafts)
        .subquery()
    )
    rows = await session.execute(
        select(
            PieceRow.facet,
            PieceRow.depth,
            Answer.question,
            Answer.understanding,
            User.name.label("askerName"),
            Craft.slug.label("craftSlug"),
            Craft.name.label("craftName"),
            asks.c.asks,
        )
        .join(Answer, Answer.id == PieceRow.createdFromAnswerId)
        .join(Craft, Craft.id == PieceRow.craftId)
        .join(asks, asks.c.craftId == PieceRow.craftId)
        .outerjoin(User, User.id == Answer.userId)
        .where(PieceRow.staleSince.is_not(None), PieceRow.supersededById.is_(None))
        .distinct()
        .order_by(asks.c.asks.desc(), Craft.slug, PieceRow.facet, PieceRow.depth, Answer.question)
    )
    return [_group(row) for row in rows]


async def run_piece_rebuild(
    groups: Sequence[StaleGroup], *, rebuild: Rebuild, remaining: Remaining, budget_usd: Decimal
) -> PieceRebuildReport:
    report = PieceRebuildReport(budget_usd=str(budget_usd))
    for group in groups:
        if await remaining() < ENRICHMENT_QUESTION_RESERVE_USD:
            report.stopped = BUDGET_STOP
            break
        outcome = RebuildOutcome(
            craft=group.craft.slug, facet=group.facet, depth=group.depth, status="FAILED"
        )
        report.groups.append(outcome)
        try:
            outcome.status = await rebuild(group)
        except AppError as error:
            outcome.error = str(error)
            if spend_refusal(error):
                report.stopped = SPEND_STOP
                break
    return report


async def rebuild_group(group: StaleGroup, pipeline: AnswerPipeline) -> str:
    sent: list[str] = []

    async def emit(name: str, payload: Any) -> None:
        sent.append(name)

    ask = AnswerAsk(
        question=group.question,
        depth=group.depth,
        craft_slug=group.craft.slug,
        withheld_terms=group.withheld_terms,
        fresh=True,
    )
    with request_id_scope(f"{PIECE_REBUILD_TAG}{uuid.uuid4().hex}"):
        await answer_understood(ask, rebuild_understanding(group), pipeline, emit)
    return REBUILT if "block" in sent else EMPTY


def rebuild_understanding(group: StaleGroup) -> Understanding:
    return Understanding(
        craft=group.craft,
        candidates=[],
        disciplines=[group.facet],
        seats=list(group.seats),
        depth=group.depth,
        language=CANONICAL_LANGUAGE,
        basis="MODEL",
    )


def _group(row: Any) -> StaleGroup:
    return StaleGroup(
        craft=CraftRef(slug=row.craftSlug, name=row.craftName, path=f"/crafts/{row.craftSlug}"),
        facet=row.facet,
        depth=row.depth,
        question=row.question,
        asks=row.asks,
        seats=_seats(row.understanding, row.depth),
        withheld_terms=withheld_name(row.askerName),
    )


def _seats(understanding: Any, depth: str) -> tuple[str, ...]:
    if not isinstance(understanding, dict):
        return ()
    try:
        stored = Understanding.model_validate(understanding)
    except ValidationError:
        logger.warning("a stored understanding no longer validates; the rebuild seats no experts")
        return ()
    return tuple(stored.seats) if stored.depth == depth else ()
