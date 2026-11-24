from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Refused
from app.models import PageDraft, PageHold, User
from app.research.page_drafts import OPEN as DRAFT_OPEN, DraftParts, part_summaries
from app.research.page_holds import (
    CONFIRMED,
    DISCARDED,
    HOLD_DAYS,
    WAITING,
    PageHoldCounts,
    PageHoldView,
    confirm_path,
    hold_expiry,
    hold_state,
)
from app.research.page_proposals import PageBundle, PageHeld, PageProposalResult, PageSubject

from . import audit
from .open_work_subjects import subject_by_key
from .page_drafts import record_submission
from .page_layouts import page_path, subject_path
from .page_renders import refuse_a_failed_drawing

__all__ = [
    "CONFIRMED_ACTION",
    "DISCARDED_ACTION",
    "HELD_ACTION",
    "NOT_WAITING",
    "HoldPlace",
    "Proposer",
    "UnknownHold",
    "confirm_hold",
    "discard_hold",
    "held_page",
    "hold_page",
]

HELD_ACTION = "page.held"
CONFIRMED_ACTION = "page.hold_confirmed"
DISCARDED_ACTION = "page.hold_discarded"
HOLD_TARGET = "PageHold"
NOT_WAITING = "not_waiting"
NO_HOLD = "No page of yours waits for confirmation with the id {id}."
NOT_OPEN = "This page is {state}, so there is nothing left to confirm or discard."
HELD = (
    "Held for one confirmation, because this account's proposals reach readers at once: nothing is proposed "
    "or shown until the person signed in to this account presses Confirm at {url}, within {days} days."
)
WAITS = "Nothing is proposed or shown until you press Confirm. Discard it to propose nothing."
DECIDED = {
    CONFIRMED: "Confirmed: each part went through its own checks.",
    DISCARDED: "Discarded: nothing was proposed.",
}
EXPIRED_MESSAGE = "It expired before anyone confirmed it, so nothing was proposed; propose the page again."

Proposer = Callable[[PageBundle], Awaitable[PageProposalResult]]


class UnknownHold(AppError):
    pass


@dataclass(frozen=True)
class HoldPlace:
    site: str
    client_name: str | None
    now: datetime


async def hold_page(
    session: AsyncSession, user: User, bundle: PageBundle, draft: PageDraft | None, place: HoldPlace
) -> PageProposalResult:
    subject = await subject_by_key(session, bundle.subject.kind, bundle.subject.slug)
    await refuse_a_failed_drawing(session, user.id, subject, now=place.now)
    await session.execute(
        update(PageHold)
        .where(
            PageHold.userId == user.id,
            PageHold.subjectKind == subject.kind,
            PageHold.subjectSlug == subject.slug,
            PageHold.state == WAITING,
        )
        .values(state=DISCARDED, decidedAt=place.now)
    )
    row = PageHold(
        userId=user.id,
        subjectKind=subject.kind,
        subjectSlug=subject.slug,
        draftId=None if draft is None else draft.id,
        draftVersion=None if draft is None else draft.version,
        bundle=bundle.model_dump(mode="json", by_alias=True),
        clientName=place.client_name,
        previewUrl=_live_preview(draft, place.now),
        createdAt=place.now,
        expiresAt=hold_expiry(place.now),
    )
    session.add(row)
    await session.flush()
    await _audited(session, HELD_ACTION, user, row)
    url = f"{place.site}{confirm_path(row.id)}"
    return PageProposalResult(
        subject=PageSubject(kind=subject.kind, slug=subject.slug),
        page_url=f"{place.site}{subject_path(subject)}",
        accepted=0,
        refused=0,
        parts=[],
        message=HELD.format(url=url, days=HOLD_DAYS),
        held=PageHeld(id=row.id, confirm_url=url, expires_at=row.expiresAt),
    )


async def held_page(
    session: AsyncSession, user: User, hold_id: uuid.UUID, *, site: str, now: datetime
) -> PageHoldView:
    return _view(await _own_hold(session, user, hold_id), site=site, now=now)


async def confirm_hold(
    session: AsyncSession, user: User, hold_id: uuid.UUID, propose: Proposer, place: HoldPlace
) -> PageHoldView:
    row = await _waiting_hold(session, user, hold_id, place.now)
    result = await propose(PageBundle.model_validate(row.bundle))
    row.state, row.decidedAt = CONFIRMED, place.now
    row.result = result.model_dump(mode="json", by_alias=True)
    await _settle_draft(session, row, result, place.now)
    await session.flush()
    await _audited(session, CONFIRMED_ACTION, user, row, accepted=result.accepted, refused=result.refused)
    return _view(row, site=place.site, now=place.now)


async def discard_hold(
    session: AsyncSession, user: User, hold_id: uuid.UUID, place: HoldPlace
) -> PageHoldView:
    row = await _waiting_hold(session, user, hold_id, place.now)
    row.state, row.decidedAt = DISCARDED, place.now
    await session.flush()
    await _audited(session, DISCARDED_ACTION, user, row)
    return _view(row, site=place.site, now=place.now)


async def _own_hold(session: AsyncSession, user: User, hold_id: uuid.UUID, *, lock: bool = False) -> PageHold:
    query = select(PageHold).where(PageHold.id == hold_id, PageHold.userId == user.id)
    if lock:
        query = query.with_for_update()
    row = await session.scalar(query)
    if row is None:
        raise UnknownHold(NO_HOLD.format(id=hold_id))
    return row


async def _waiting_hold(session: AsyncSession, user: User, hold_id: uuid.UUID, now: datetime) -> PageHold:
    row = await _own_hold(session, user, hold_id, lock=True)
    state = hold_state(row.state, row.expiresAt, now=now)
    if state != WAITING:
        raise Refused(NOT_WAITING, NOT_OPEN.format(state=state.lower()))
    return row


async def _settle_draft(
    session: AsyncSession, row: PageHold, result: PageProposalResult, now: datetime
) -> None:
    if row.draftId is None:
        return
    draft = await session.get(PageDraft, row.draftId, with_for_update=True)
    if draft is not None and draft.state == DRAFT_OPEN and draft.version == row.draftVersion:
        await record_submission(session, draft, result, now=now)


async def _audited(session: AsyncSession, action: str, user: User, row: PageHold, **counts: int) -> None:
    await audit.record(
        session,
        action=action,
        actor=user,
        target_type=HOLD_TARGET,
        target_id=row.id,
        detail={"page": f"{row.subjectKind}:{row.subjectSlug}", "client": row.clientName, **counts},
    )
    await session.flush()


def _live_preview(draft: PageDraft | None, now: datetime) -> str | None:
    if draft is None or draft.previewUrl is None or draft.previewExpiresAt is None:
        return None
    return draft.previewUrl if draft.previewExpiresAt > now else None


def _view(row: PageHold, *, site: str, now: datetime) -> PageHoldView:
    bundle = PageBundle.model_validate(row.bundle)
    state = hold_state(row.state, row.expiresAt, now=now)
    subject = PageSubject(kind=row.subjectKind, slug=row.subjectSlug)
    return PageHoldView(
        id=row.id,
        subject=subject,
        page_url=f"{site}{page_path(subject.kind, subject.slug)}",
        state=state,
        client_name=row.clientName,
        created_at=row.createdAt,
        expires_at=row.expiresAt,
        decided_at=row.decidedAt,
        counts=_counts(bundle),
        parts=part_summaries(_parts(bundle)),
        preview_url=row.previewUrl if state == WAITING else None,
        result=None if row.result is None else PageProposalResult.model_validate(row.result),
        message=DECIDED.get(state, WAITS if state == WAITING else EXPIRED_MESSAGE),
    )


def _parts(bundle: PageBundle) -> DraftParts:
    return DraftParts(
        facts=list(bundle.facts),
        structure=list(bundle.structure),
        components=list(bundle.components),
        layout=bundle.layout,
        pictures=list(bundle.pictures),
        withdrawals=list(bundle.withdrawals),
        note=bundle.note,
    )


def _counts(bundle: PageBundle) -> PageHoldCounts:
    return PageHoldCounts(
        facts=len(bundle.facts),
        structure=len(bundle.structure),
        components=len(bundle.components),
        layout=int(bundle.layout is not None),
        pictures=len(bundle.pictures),
        withdrawals=len(bundle.withdrawals),
        translations=0 if bundle.translation is None else len(bundle.translation.passages),
    )
