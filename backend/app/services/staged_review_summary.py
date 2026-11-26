from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StagedReview, StagedReviewItem, User
from app.research.staged_review_words import decision_words
from app.research.staged_reviews import OPEN, StagedDecision, batch_status

from .page_proposal_reviews import page_touches
from .staged_review_views import batch_items

__all__ = ["StagedLineWords", "StagedSummary", "own_open_batch", "staged_summary"]


@dataclass(frozen=True)
class StagedLineWords:
    position: int
    item_id: uuid.UUID
    label: str
    words: str


@dataclass(frozen=True)
class StagedSummary:
    batch_id: uuid.UUID
    client_name: str
    expires_at: datetime
    lines: tuple[StagedLineWords, ...]


async def own_open_batch(
    session: AsyncSession, batch_id: uuid.UUID, person: User, *, grant_id: uuid.UUID | None, now: datetime
) -> StagedReview | None:
    batch = await session.get(StagedReview, batch_id, populate_existing=True)
    if batch is None or batch.proposerId != person.id:
        return None
    if batch.grantId is not None and batch.grantId != grant_id:
        return None
    return batch if batch_status(batch.status, batch.expiresAt, now=now) == OPEN else None


async def staged_summary(session: AsyncSession, batch: StagedReview, *, site: str) -> StagedSummary:
    lines = [await _line(session, item, site=site) for item in await batch_items(session, batch.id)]
    return StagedSummary(batch.id, batch.clientName, batch.expiresAt, tuple(lines))


async def _line(session: AsyncSession, item: StagedReviewItem, *, site: str) -> StagedLineWords:
    decision = StagedDecision.model_validate(item.decision)
    touches = (
        None if decision.page is None else await page_touches(session, decision.id, decision.page, site=site)
    )
    words = decision_words(decision, item.label, touches=touches)
    return StagedLineWords(item.position, item.id, item.label, words)
