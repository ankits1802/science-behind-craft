from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, InvalidInput
from app.models import PageProposal, User
from app.research.page_proposal_review import (
    APPLIED,
    REFUSED,
    SKIPPED,
    WAITING,
    PageDecision,
    PageDecisionBody,
    PartOutcome,
    ProposalPart,
    parts_in_scope,
    scope_words,
)
from app.research.page_revalidation import PageOwners
from app.research.review_queue import APPROVE, QueueApproval, QueueDecision, QueueRejection

from . import audit
from .page_proposal_reviews import part_states, reviewable, stored_parts
from .page_revalidation import merged_owners
from .review_queue_decisions import ItemRef, approve_item, reject_item
from .review_queue_errors import refusal_of
from .review_queue_refresh import decision_owners

__all__ = ["PAGE_DECIDED", "PageDecided", "decide_page"]

PAGE_DECIDED = "review.page_{action}"
NOTHING_IN_SCOPE = "Nothing in {scope} waits in this page proposal; open it again to see each part's state."
NOT_WAITING = "Already decided: it is {state} and was left as it is."
DECIDED = "{action} {scope}: {applied} parts {verb}, {refused} refused by their own checks and {skipped} already decided."
PAST = {"approve": "approved", "reject": "rejected"}


@dataclass
class PageDecided:
    decision: PageDecision
    message: str
    owners: PageOwners = field(default_factory=PageOwners)
    decided: list[QueueDecision] = field(default_factory=list)
    open: bool = True


async def decide_page(
    session: AsyncSession, reviewer: User, proposal_id: uuid.UUID, body: PageDecisionBody, *, now: datetime
) -> PageDecided:
    row = await reviewable(session, reviewer, proposal_id, lock=True)
    scope = body.scoped()
    parts = parts_in_scope(stored_parts(row), scope)
    if not parts:
        raise InvalidInput(NOTHING_IN_SCOPE.format(scope=scope_words(scope)))
    states = await part_states(session, parts)
    outcomes: list[PartOutcome] = []
    decided: list[QueueDecision] = []
    for part in parts:
        state = states.get(part.id)
        if state != WAITING:
            outcomes.append(_outcome(part, SKIPPED, NOT_WAITING.format(state=str(state or "gone").lower())))
            continue
        outcome, made = await _applied(session, reviewer, part, body, now=now)
        outcomes.append(outcome)
        if made is not None:
            decided.append(made)
    decision = PageDecision.model_validate({**body.model_dump(), "decidedAt": now, "outcomes": outcomes})
    still = await _kept(session, row, reviewer, decision, now=now)
    owners = merged_owners(*[await decision_owners(session, made) for made in decided])
    return PageDecided(decision, _message(decision, scope_words(scope)), owners, decided, open=still)


async def _applied(
    session: AsyncSession, reviewer: User, part: ProposalPart, body: PageDecisionBody, *, now: datetime
) -> tuple[PartOutcome, QueueDecision | None]:
    ref = ItemRef(part.kind, part.id)
    savepoint = await session.begin_nested()
    try:
        if body.action == APPROVE:
            made = await approve_item(session, ref, reviewer, QueueApproval(note=body.note), now=now)
        else:
            made = await reject_item(session, ref, reviewer, QueueRejection(reason=body.note), now=now)
    except (AppError, ValidationError) as refused:
        await savepoint.rollback()
        return _outcome(part, REFUSED, refusal_of(refused)), None
    await savepoint.commit()
    return _outcome(part, APPLIED, made.message), made


async def _kept(
    session: AsyncSession, row: PageProposal, reviewer: User, decision: PageDecision, *, now: datetime
) -> bool:
    stored = {"decision": decision.model_dump(mode="json"), "reviewerId": str(reviewer.id)}
    row.decisions = [*row.decisions, stored]
    states = await part_states(session, stored_parts(row))
    still = WAITING in states.values()
    if not still:
        row.closedAt = now
    await audit.record(
        session,
        action=PAGE_DECIDED.format(action=PAST[decision.action]),
        actor=reviewer,
        target_type="PageProposal",
        target_id=row.id,
        detail={"scope": decision.scope, "chapter": decision.chapter, "label": decision.label},
    )
    await session.flush()
    return still


def _outcome(part: ProposalPart, outcome: str, message: str) -> PartOutcome:
    return PartOutcome.model_validate(
        {
            "part": part.part,
            "kind": part.kind,
            "id": part.id,
            "title": part.title,
            "outcome": outcome,
            "message": message,
        }
    )


def _message(decision: PageDecision, scope: str) -> str:
    marks = [outcome.outcome for outcome in decision.outcomes]
    return DECIDED.format(
        action=PAST[decision.action].capitalize(),
        scope=scope,
        applied=marks.count(APPLIED),
        verb=PAST[decision.action],
        refused=marks.count(REFUSED),
        skipped=marks.count(SKIPPED),
    )
