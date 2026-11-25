from __future__ import annotations

import uuid
from datetime import datetime
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import Chunk, Claim, ClaimSource, ReviewEvent, User
from app.research.published_edits import FactEdit, fact_text_problems
from app.research.quotes import quote_occurs
from app.research.retrieval import SHOWN_CLAIM_STATUSES
from app.research.review_labels import cut_label
from app.research.staged_reviews import EDIT, StagedDecision

from . import audit
from .page_revalidation import claim_owners
from .published_kinds import NO_ITEM, Carried, Editable, PublishedKind, PublishedRef, checked_edit

__all__ = ["FACT_EDITED", "PUBLISHED_FACTS", "quote_problems"]

FACT_EDITED = "fact.edited"
EDITED = "Edited: the fact reads as changed on every page that shows it, and its earlier text is kept in the record."
REFUSED = "The new text fails the quote check the fact passed: {problems}"
GONE = "quote {number} ({locator}) is no longer in the passage stored for its source"
NO_LOCATOR = "no locator"
USER = "USER"


async def _claim(session: AsyncSession, claim_id: uuid.UUID, *, lock: bool = False) -> Claim | None:
    query = select(Claim).where(Claim.id == claim_id, Claim.status.in_(SHOWN_CLAIM_STATUSES))
    return await session.scalar(
        query.with_for_update().execution_options(populate_existing=True) if lock else query
    )


async def _name(session: AsyncSession, ref: PublishedRef) -> str | None:
    claim = await _claim(session, ref.id)
    return None if claim is None else cut_label(f"Fact: {claim.text}")


async def _editable(session: AsyncSession, ref: PublishedRef) -> Editable | None:
    claim = await _claim(session, ref.id)
    return None if claim is None else Editable({"text": claim.text}, FactEdit)


async def quote_problems(session: AsyncSession, claim_id: uuid.UUID, text: str) -> list[str]:
    cited = (
        await session.execute(
            select(ClaimSource.quote, ClaimSource.locator, Chunk.text)
            .outerjoin(Chunk, Chunk.id == ClaimSource.chunkId)
            .where(ClaimSource.claimId == claim_id, ClaimSource.quote.is_not(None))
            .order_by(ClaimSource.createdAt, ClaimSource.id)
        )
    ).all()
    quotes = [str(quote) for quote, _, _ in cited]
    problems = fact_text_problems(text, quotes)
    for number, (quote, locator, passage) in enumerate(cited, start=1):
        if passage is not None and not quote_occurs(str(quote), passage):
            problems.append(GONE.format(number=number, locator=locator or NO_LOCATOR))
    return problems


async def _edit(session: AsyncSession, decision: StagedDecision, reviewer: User, _now: datetime) -> Carried:
    claim = await _claim(session, decision.id, lock=True)
    if claim is None:
        raise InvalidInput(NO_ITEM.format(kind="fact", id=decision.id))
    before = claim.text
    text = str(checked_edit(decision, Editable({"text": before}, FactEdit))["text"])
    problems = await quote_problems(session, claim.id, text)
    if problems:
        raise InvalidInput(REFUSED.format(problems="; ".join(problems)))
    claim.text, claim.version = text, claim.version + 1
    claim.embedding, claim.embeddingModel = None, None
    session.add(
        ReviewEvent(
            claimId=claim.id,
            actorId=reviewer.id,
            actorKind=USER,
            fromStatus=claim.status,
            toStatus=claim.status,
            fromLevel=claim.evidenceLevel,
            toLevel=claim.evidenceLevel,
            note=f"Text edited: {decision.reason}",
        )
    )
    await audit.record(
        session,
        action=FACT_EDITED,
        actor=reviewer,
        target_type="Claim",
        target_id=claim.id,
        detail={"before": before, "after": text, "reason": decision.reason},
    )
    await session.flush()
    return Carried(EDITED, await claim_owners(session, [claim.id]), marks=(str(claim.id),))


PUBLISHED_FACTS = PublishedKind(
    noun="fact", name=_name, actions=MappingProxyType({EDIT: _edit}), editable=_editable
)
