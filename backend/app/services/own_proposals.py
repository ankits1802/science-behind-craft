from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Refused
from app.models import AuditLog, CandidateCheck, Claim, ComponentProposal, Concept, Craft, ReviewEvent, User
from app.research.candidate_gates import GATES
from app.research.component_proposals import ComponentProposalResult
from app.research.knowledge_writes import GateReport
from app.research.own_proposals import (
    COMPONENT,
    CONTRIBUTION_TERMS_VERSION,
    FACT,
    OWN_PROPOSALS_MAX,
    ComponentProposalBody,
    OwnProposal,
    OwnProposals,
    ProposalForm,
    TermsAcceptance,
    TermsStatus,
    component_reasons,
    component_state,
    fact_reasons,
    fact_state,
    newest_first,
    withdraw_refusal,
)

from . import audit
from .component_proposals import propose_component
from .knowledge_api import field_list
from .proposal_writes import PROPOSAL_CLAIM_ORIGIN, PROPOSAL_PREDICATE

__all__ = [
    "NOT_WAITING",
    "TERMS_ACCEPTED",
    "TERMS_NEEDED",
    "UnknownProposal",
    "accept_terms",
    "own_proposals",
    "proposal_form",
    "propose_on_site",
    "require_terms",
    "terms_status",
    "withdraw_component",
    "withdraw_fact",
]

USER_ACTOR = "USER"
CONCEPT_SUBJECT = "CONCEPT"
WAITING_FACT = "DRAFT"
WAITING_COMPONENT = "PENDING"
WITHDRAWN_STATUS = "WITHDRAWN"
REJECTED_STATUS = "REJECTED"
WITHDRAWN_NOTE = "withdrawn by its proposer while it waited for review"
TERMS_ACCEPTED = "contributions.terms_accepted"
TERMS_TARGET = "ContributionTerms"
NOT_WAITING = "not_waiting"
TERMS_NEEDED = "terms_needed"
TERMS_MISSING = "Accept the contribution terms, version {version}, before you propose."
NO_SUCH_PROPOSAL = "No proposal of yours has that id."


class UnknownProposal(AppError):
    pass


async def own_proposals(session: AsyncSession, user: User) -> OwnProposals:
    facts = await _fact_items(session, user.id)
    components = await _component_items(session, user.id)
    return OwnProposals(items=newest_first([*facts, *components]))


async def withdraw_fact(session: AsyncSession, user: User, claim_id: uuid.UUID) -> OwnProposal:
    status = await session.scalar(
        select(Claim.status).where(Claim.id == claim_id, *_own_facts(user.id)).with_for_update()
    )
    if status is None:
        raise UnknownProposal(NO_SUCH_PROPOSAL)
    _refuse_unless_waiting(fact_state(status, []))
    await session.execute(update(Claim).where(Claim.id == claim_id).values(status=WITHDRAWN_STATUS))
    session.add(
        ReviewEvent(
            claimId=claim_id,
            actorId=user.id,
            actorKind=USER_ACTOR,
            fromStatus=WAITING_FACT,
            toStatus=WITHDRAWN_STATUS,
            note=WITHDRAWN_NOTE,
        )
    )
    await session.flush()
    (item,) = await _fact_items(session, user.id, Claim.id == claim_id)
    return item


async def withdraw_component(session: AsyncSession, user: User, proposal_id: uuid.UUID) -> OwnProposal:
    status = await session.scalar(
        select(ComponentProposal.status)
        .where(ComponentProposal.id == proposal_id, ComponentProposal.proposerId == user.id)
        .with_for_update()
    )
    if status is None:
        raise UnknownProposal(NO_SUCH_PROPOSAL)
    _refuse_unless_waiting(component_state(status))
    await session.execute(
        update(ComponentProposal)
        .where(ComponentProposal.id == proposal_id, ComponentProposal.status == WAITING_COMPONENT)
        .values(status=WITHDRAWN_STATUS)
    )
    await session.flush()
    (item,) = await _component_items(session, user.id, ComponentProposal.id == proposal_id)
    return item


async def terms_status(session: AsyncSession, user: User) -> TermsStatus:
    accepted = await session.scalar(
        select(func.min(AuditLog.createdAt)).where(
            AuditLog.actorId == user.id,
            AuditLog.action == TERMS_ACCEPTED,
            AuditLog.targetId == CONTRIBUTION_TERMS_VERSION,
        )
    )
    return TermsStatus(version=CONTRIBUTION_TERMS_VERSION, accepted_at=accepted)


async def accept_terms(session: AsyncSession, user: User, acceptance: TermsAcceptance) -> TermsStatus:
    held = await terms_status(session, user)
    if held.accepted_at is not None:
        return held
    await audit.record(
        session,
        action=TERMS_ACCEPTED,
        actor=user,
        target_type=TERMS_TARGET,
        target_id=acceptance.version,
        detail={"version": acceptance.version},
    )
    await session.flush()
    return await terms_status(session, user)


async def require_terms(session: AsyncSession, user: User) -> None:
    if (await terms_status(session, user)).accepted_at is None:
        raise Refused(TERMS_NEEDED, TERMS_MISSING.format(version=CONTRIBUTION_TERMS_VERSION))


async def proposal_form(session: AsyncSession, user: User) -> ProposalForm:
    return ProposalForm(terms=await terms_status(session, user), fields=field_list().fields)


async def propose_on_site(
    session: AsyncSession, user: User, body: ComponentProposalBody, *, now: datetime
) -> ComponentProposalResult:
    await require_terms(session, user)
    return await propose_component(session, user, body, now=now)


def _own_facts(user_id: uuid.UUID) -> list[ColumnElement[bool]]:
    return [
        Claim.createdById == user_id,
        Claim.createdByKind == USER_ACTOR,
        Claim.origin == PROPOSAL_CLAIM_ORIGIN,
        Claim.predicate == PROPOSAL_PREDICATE,
        Claim.subjectType == CONCEPT_SUBJECT,
    ]


def _refuse_unless_waiting(state: str) -> None:
    refusal = withdraw_refusal(state)
    if refusal is not None:
        raise Refused(NOT_WAITING, refusal)


async def _fact_items(
    session: AsyncSession, user_id: uuid.UUID, *narrowed: ColumnElement[bool]
) -> list[OwnProposal]:
    rows = (
        await session.execute(
            select(Claim.id, Claim.text, Claim.status, Claim.field, Claim.createdAt, Concept.name, Craft.slug)
            .outerjoin(Concept, Concept.id == Claim.subjectId)
            .outerjoin(Craft, Craft.id == Concept.craftId)
            .where(*_own_facts(user_id), *narrowed)
            .order_by(Claim.createdAt.desc(), Claim.id)
            .limit(OWN_PROPOSALS_MAX)
        )
    ).all()
    ids = [row.id for row in rows]
    gates = await _gates(session, ids)
    notes = await _reviewer_notes(session, user_id, ids)
    return [_fact_item(row, gates.get(row.id, []), notes.get(row.id)) for row in rows]


def _fact_item(row: Any, gates: list[GateReport], note: str | None) -> OwnProposal:
    state = fact_state(row.status, gates)
    return OwnProposal(
        id=row.id,
        kind=FACT,
        state=state,
        status=row.status,
        text=row.text,
        field=row.field,
        subject_name=row.name,
        craft_slug=row.slug,
        created_at=row.createdAt,
        reasons=fact_reasons(state, gates, note),
        gates=gates,
    )


async def _component_items(
    session: AsyncSession, user_id: uuid.UUID, *narrowed: ColumnElement[bool]
) -> list[OwnProposal]:
    rows = (
        await session.execute(
            select(ComponentProposal, Craft.name, Craft.slug)
            .outerjoin(Craft, Craft.id == ComponentProposal.craftId)
            .where(ComponentProposal.proposerId == user_id, *narrowed)
            .order_by(ComponentProposal.createdAt.desc(), ComponentProposal.id)
            .limit(OWN_PROPOSALS_MAX)
        )
    ).all()
    return [_component_item(proposal, name, slug) for proposal, name, slug in rows]


def _component_item(proposal: ComponentProposal, craft_name: str | None, slug: str | None) -> OwnProposal:
    state = component_state(proposal.status)
    return OwnProposal(
        id=proposal.id,
        kind=COMPONENT,
        state=state,
        status=proposal.status,
        text=proposal.title,
        description=proposal.description,
        label=proposal.label,
        component_kind=proposal.kind,
        field=proposal.field,
        subject_name=craft_name,
        craft_slug=slug,
        created_at=proposal.createdAt,
        reasons=component_reasons(state, proposal.reviewNote),
    )


async def _gates(session: AsyncSession, claim_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[GateReport]]:
    if not claim_ids:
        return {}
    rows = await session.scalars(select(CandidateCheck).where(CandidateCheck.claimId.in_(list(claim_ids))))
    found: dict[uuid.UUID, list[GateReport]] = {}
    for check in sorted(rows, key=lambda row: GATES.index(row.gate)):
        report = GateReport(gate=check.gate, passed=check.passed, reasons=list(check.reasons))
        found.setdefault(check.claimId, []).append(report)
    return found


async def _reviewer_notes(
    session: AsyncSession, user_id: uuid.UUID, claim_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not claim_ids:
        return {}
    rows = await session.execute(
        select(ReviewEvent.claimId, ReviewEvent.note)
        .where(
            and_(
                ReviewEvent.claimId.in_(list(claim_ids)),
                ReviewEvent.toStatus == REJECTED_STATUS,
                ReviewEvent.actorKind == USER_ACTOR,
                ReviewEvent.actorId.is_distinct_from(user_id),
                ReviewEvent.note.is_not(None),
            )
        )
        .order_by(ReviewEvent.claimId, ReviewEvent.createdAt.desc(), ReviewEvent.id)
    )
    found: dict[uuid.UUID, str] = {}
    for claim_id, note in rows.all():
        found.setdefault(claim_id, note)
    return found
