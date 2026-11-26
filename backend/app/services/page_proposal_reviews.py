from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.core.roles import Capability, can
from app.models import (
    Claim,
    ComponentProposal,
    ImageContribution,
    LayoutProposal,
    PageProposal,
    StructureProposal,
    User,
)
from app.research.page_changes import ChapterChanges
from app.research.page_proposal_review import (
    AFTER,
    APPROVED,
    BEFORE,
    CLOSED,
    REJECTED,
    WAITING,
    PageDecision,
    PageProposalList,
    PageProposalView,
    PageReviewNote,
    PageScope,
    PartView,
    ProposalPart,
    scope_words,
)
from app.research.page_proposals import PageSubject
from app.research.review_labels import cut_label
from app.research.review_queue import COMPONENTS, FACTS, IMAGES, LAYOUTS, STRUCTURE
from app.research.review_queue_items import Proposer

from .open_work_subjects import subject_by_key
from .page_layouts import page_path
from .page_proposal_pictures import picture_views
from .review_queue_errors import NotYourQueue, OwnItem, UnknownItem

__all__ = [
    "LISTED_MAX",
    "NOTES_SHOWN_MAX",
    "OPEN_WINDOW",
    "open_page_proposals",
    "page_label",
    "page_proposal",
    "page_review_notes",
    "part_states",
    "proposal_document",
    "reviewable",
    "stored_parts",
]

OPEN_WINDOW = timedelta(days=60)
NOTES_WINDOW = timedelta(days=30)
LISTED_MAX = 20
READ_MAX = 60
NOTES_SHOWN_MAX = 10
NOT_AN_ADMIN = "Page proposals are reviewed by Admins and Master Admins."
NO_PROPOSAL = "No page proposal has the id {id}."
OWN = "A reviewer does not decide their own page proposal."
NO_DOCUMENT = "This page proposal keeps no drawing of the page {side}."
SIDE_WORDS = MappingProxyType({BEFORE: "as it stood", AFTER: "as it will be"})
LABEL = "Page proposal for {name}: {scope}"
STATES = MappingProxyType(
    {
        "DRAFT": WAITING,
        "IN_REVIEW": WAITING,
        "PENDING": WAITING,
        "APPROVED": APPROVED,
        "REJECTED": REJECTED,
        "RETRACTED": REJECTED,
    }
)
MODELS: Any = MappingProxyType(
    {
        FACTS: Claim,
        STRUCTURE: StructureProposal,
        IMAGES: ImageContribution,
        COMPONENTS: ComponentProposal,
        LAYOUTS: LayoutProposal,
    }
)


async def open_page_proposals(
    session: AsyncSession, viewer: User, *, site: str, now: datetime
) -> PageProposalList:
    _reviewer(viewer)
    rows = await session.scalars(
        select(PageProposal)
        .where(
            PageProposal.closedAt.is_(None),
            PageProposal.userId != viewer.id,
            PageProposal.createdAt >= now - OPEN_WINDOW,
        )
        .order_by(PageProposal.createdAt.desc(), PageProposal.id.desc())
        .limit(READ_MAX)
    )
    shown: list[PageProposalView] = []
    for row in rows.all():
        view = await _view(session, row, viewer, site=site, whole=False)
        if view.waiting:
            shown.append(view)
        if len(shown) == LISTED_MAX:
            break
    return PageProposalList(proposals=shown)


async def page_proposal(
    session: AsyncSession, viewer: User, proposal_id: uuid.UUID, *, site: str
) -> PageProposalView:
    row = await reviewable(session, viewer, proposal_id)
    return await _view(session, row, viewer, site=site, whole=True)


async def reviewable(
    session: AsyncSession, viewer: User, proposal_id: uuid.UUID, *, lock: bool = False
) -> PageProposal:
    _reviewer(viewer)
    row = await session.get(PageProposal, proposal_id, with_for_update=lock)
    if row is None:
        raise UnknownItem(NO_PROPOSAL.format(id=proposal_id))
    if row.userId == viewer.id:
        raise OwnItem(OWN)
    return row


async def proposal_document(
    session: AsyncSession, viewer: User, proposal_id: uuid.UUID, side: str
) -> dict[str, Any]:
    await reviewable(session, viewer, proposal_id)
    column = PageProposal.before if side == BEFORE else PageProposal.after
    document = await session.scalar(select(column).where(PageProposal.id == proposal_id))
    if document is None:
        raise UnknownItem(NO_DOCUMENT.format(side=SIDE_WORDS[side]))
    return dict(document)


def stored_parts(row: PageProposal) -> list[ProposalPart]:
    return [ProposalPart.model_validate(part) for part in row.parts]


async def part_states(session: AsyncSession, parts: Sequence[ProposalPart]) -> dict[uuid.UUID, str]:
    found: dict[uuid.UUID, str] = {}
    for kind, model in MODELS.items():
        ids = [part.id for part in parts if part.kind == kind]
        if not ids:
            continue
        rows = await session.execute(select(model.id, model.status).where(model.id.in_(ids)))
        found |= {ident: STATES.get(str(status), CLOSED) for ident, status in rows.all()}
    return found


async def page_label(session: AsyncSession, proposal_id: uuid.UUID, scope: PageScope) -> str | None:
    row = await session.get(PageProposal, proposal_id)
    if row is None:
        return None
    name = await _subject_name(session, row.subjectKind, row.subjectSlug)
    return cut_label(LABEL.format(name=name, scope=scope_words(scope)))


async def page_review_notes(
    session: AsyncSession, user_id: uuid.UUID, *, now: datetime
) -> list[PageReviewNote]:
    rows = await session.scalars(
        select(PageProposal)
        .where(PageProposal.userId == user_id, PageProposal.createdAt >= now - NOTES_WINDOW)
        .order_by(PageProposal.createdAt.desc())
    )
    notes = [
        _note(row, PageDecision.model_validate(stored["decision"]))
        for row in rows.all()
        for stored in row.decisions
    ]
    return sorted(notes, key=lambda note: note.decided_at, reverse=True)[:NOTES_SHOWN_MAX]


def _note(row: PageProposal, decision: PageDecision) -> PageReviewNote:
    return PageReviewNote.model_validate(
        {
            **decision.model_dump(),
            "proposalId": row.id,
            "subject": PageSubject.model_validate({"kind": row.subjectKind, "slug": row.subjectSlug}),
        }
    )


async def _view(
    session: AsyncSession, row: PageProposal, viewer: User, *, site: str, whole: bool
) -> PageProposalView:
    parts = stored_parts(row)
    states = await part_states(session, parts)
    shown = [
        PartView.model_validate({**part.model_dump(), "state": states.get(part.id, CLOSED)}) for part in parts
    ]
    chapters = [ChapterChanges.model_validate(chapter) for chapter in row.changes]
    sides = (await session.execute(_sides(row.id))).one()
    return PageProposalView(
        id=row.id,
        subject=PageSubject.model_validate({"kind": row.subjectKind, "slug": row.subjectSlug}),
        subject_name=await _subject_name(session, row.subjectKind, row.subjectSlug),
        page_url=f"{site}{page_path(row.subjectKind, row.subjectSlug)}",
        origin=row.origin,
        proposer=await _proposer(session, row.userId)
        if can(viewer, Capability.REVIEW_CONTRIBUTIONS)
        else None,
        created_at=row.createdAt,
        waiting=sum(part.state == WAITING for part in shown),
        parts=shown,
        chapters=chapters if whole else [chapter.model_copy(update={"changes": []}) for chapter in chapters],
        pictures=await picture_views(session, row.id),
        drawable=[side for side, kept in zip((BEFORE, AFTER), sides, strict=True) if kept],
        decisions=[PageDecision.model_validate(stored["decision"]) for stored in row.decisions],
        whole=whole,
    )


def _sides(proposal_id: uuid.UUID) -> Any:
    return select(PageProposal.before.is_not(None), PageProposal.after.is_not(None)).where(
        PageProposal.id == proposal_id
    )


async def _proposer(session: AsyncSession, user_id: uuid.UUID) -> Proposer | None:
    found = (await session.execute(select(User.name, User.role).where(User.id == user_id))).first()
    if found is None:
        return None
    return Proposer(name=found.name, role=str(getattr(found.role, "value", found.role)))


async def _subject_name(session: AsyncSession, kind: str, slug: str) -> str:
    try:
        return (await subject_by_key(session, kind, slug)).name
    except InvalidInput:
        return slug.replace("-", " ")


def _reviewer(viewer: User) -> None:
    if not can(viewer, Capability.REVIEW_CONTRIBUTIONS):
        raise NotYourQueue(NOT_AN_ADMIN)
