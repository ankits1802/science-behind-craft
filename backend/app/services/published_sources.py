from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from types import MappingProxyType
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import Claim, ClaimSource, ConditionReading, KnowledgePiece, Source, User
from app.research.retrieval import SHOWN_CLAIM_STATUSES
from app.research.review_labels import cut_label
from app.research.staged_reviews import REMOVE, StagedDecision

from . import audit
from .page_revalidation import claim_owners
from .published_kinds import NO_ITEM, Carried, PublishedKind, PublishedRef

__all__ = ["PUBLISHED_SOURCES", "SOURCE_REMOVED"]

SOURCE_REMOVED = "source.removed"
LIVE_STATUSES = (*SHOWN_CLAIM_STATUSES, "DRAFT")
NAMED_MAX = 10
CITATIONS_KEPT = 500
REMOVED = (
    "Removed: {title} is unlinked from the {facts} facts that cited it beside other sources, and its record, "
    "each quote it gave and the reason are kept."
)
ONLY_SOURCE = (
    "These facts cite only {title}, so removing it would leave them unsourced: {facts}. Retract them, or give "
    "each another source with propose_source, then stage the removal anew."
)
READ_FROM = (
    "The readings read from {title}'s quotes ({count}) would go with them: remove those readings first, then "
    "stage the removal anew."
)
LAST_SOURCE = (
    "{title} is the only source left to {pieces}, which would rest on none: remove or replace them first."
)


async def _name(session: AsyncSession, ref: PublishedRef) -> str | None:
    title = await session.scalar(select(Source.title).where(Source.id == ref.id))
    return None if title is None else cut_label(f"Source: {title}")


async def _remove(session: AsyncSession, decision: StagedDecision, reviewer: User, _now: datetime) -> Carried:
    source = await session.get(Source, decision.id, with_for_update=True, populate_existing=True)
    if source is None:
        raise InvalidInput(NO_ITEM.format(kind="source", id=decision.id))
    cited = (
        await session.execute(
            select(ClaimSource.id, ClaimSource.claimId, ClaimSource.quote, ClaimSource.locator)
            .where(ClaimSource.sourceId == source.id)
            .order_by(ClaimSource.claimId, ClaimSource.id)
        )
    ).all()
    claim_ids = sorted({row.claimId for row in cited})
    await _refuse_orphans(session, source, claim_ids)
    await _refuse_readings(session, source, [row.id for row in cited])
    pieces = await _unlinked_pieces(session, source)
    await session.execute(delete(ClaimSource).where(ClaimSource.sourceId == source.id))
    await audit.record(
        session,
        action=SOURCE_REMOVED,
        actor=reviewer,
        target_type="Source",
        target_id=source.id,
        detail={
            "title": source.title,
            "citations": [_citation(row) for row in cited[:CITATIONS_KEPT]],
            "cited": len(cited),
            "pieces": pieces,
            "reason": decision.reason,
        },
    )
    await session.flush()
    message = REMOVED.format(title=source.title, facts=len(claim_ids))
    return Carried(message, await claim_owners(session, claim_ids))


def _citation(row: Any) -> dict[str, Any]:
    return {"claim": str(row.claimId), "quote": row.quote, "locator": row.locator}


async def _refuse_orphans(session: AsyncSession, source: Source, claim_ids: Sequence[uuid.UUID]) -> None:
    if not claim_ids:
        return
    elsewhere = select(ClaimSource.claimId).where(
        ClaimSource.claimId.in_(list(claim_ids)), ClaimSource.sourceId != source.id
    )
    alone = await session.execute(
        select(Claim.id, Claim.text)
        .where(Claim.id.in_(list(claim_ids)), Claim.status.in_(LIVE_STATUSES), Claim.id.not_in(elsewhere))
        .order_by(Claim.id)
        .limit(NAMED_MAX)
    )
    named = [f"{claim_id} ({cut_label(text)})" for claim_id, text in alone.tuples().all()]
    if named:
        raise InvalidInput(ONLY_SOURCE.format(title=source.title, facts="; ".join(named)))


async def _refuse_readings(session: AsyncSession, source: Source, citation_ids: Sequence[uuid.UUID]) -> None:
    if not citation_ids:
        return
    counted = await session.scalar(
        select(func.count(ConditionReading.id)).where(ConditionReading.claimSourceId.in_(list(citation_ids)))
    )
    if counted:
        raise InvalidInput(READ_FROM.format(count=counted, title=source.title))


async def _unlinked_pieces(session: AsyncSession, source: Source) -> int:
    held = str(source.id)
    pieces = list(
        await session.scalars(
            select(KnowledgePiece)
            .where(KnowledgePiece.sourceIds.contains([held]))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    stranded = [piece.label or str(piece.id) for piece in pieces if set(piece.sourceIds) == {held}]
    if stranded:
        raise InvalidInput(LAST_SOURCE.format(title=source.title, pieces=", ".join(stranded[:NAMED_MAX])))
    for piece in pieces:
        piece.sourceIds = [kept for kept in piece.sourceIds if kept != held]
    return len(pieces)


PUBLISHED_SOURCES = PublishedKind(noun="source", name=_name, actions=MappingProxyType({REMOVE: _remove}))
