from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.core.roles import Capability, can
from app.models import KnowledgePiece, User
from app.research.page_revalidation import PageOwners
from app.research.review_labels import cut_label
from app.research.review_queue import COMPONENTS
from app.research.staged_reviews import REMOVE, StagedDecision

from .component_library_applies import registered_pieces
from .component_lifecycle import take_off_pages
from .open_work_subjects import CATEGORY, WorkSubject, craft_subject, subject_by_key
from .review_queue_errors import NotYourQueue

__all__ = ["PUBLISHED_KINDS", "Carried", "PublishedKind", "carry_out", "published_id", "published_label"]

NOT_AN_ADMIN = "Changing published content is for Admins and Master Admins."
NO_ITEM = "No published {kind} has the id {id}."
REMOVED_EVERYWHERE = "Removed: {label} is off every page that placed it, and kept in the record."
REMOVED_FROM = "Removed from {page}'s page: {label} stays on every other page that places it."


@dataclass(frozen=True)
class Carried:
    message: str
    owners: PageOwners


Labeller = Callable[[AsyncSession, StagedDecision], Awaitable[str | None]]
Finder = Callable[[AsyncSession, str], Awaitable[uuid.UUID | None]]
Doer = Callable[[AsyncSession, StagedDecision, User, datetime], Awaitable[Carried]]


@dataclass(frozen=True)
class PublishedKind:
    label: Labeller
    find: Finder
    actions: Mapping[str, Doer]


async def published_label(session: AsyncSession, decision: StagedDecision) -> str | None:
    return await PUBLISHED_KINDS[decision.kind].label(session, decision)


async def published_id(session: AsyncSession, kind: str, label: str) -> uuid.UUID | None:
    handled = PUBLISHED_KINDS.get(kind)
    return None if handled is None else await handled.find(session, label)


async def carry_out(
    session: AsyncSession, decision: StagedDecision, reviewer: User, *, now: datetime
) -> Carried:
    if not can(reviewer, Capability.REVIEW_CONTRIBUTIONS):
        raise NotYourQueue(NOT_AN_ADMIN)
    return await PUBLISHED_KINDS[decision.kind].actions[decision.action](session, decision, reviewer, now)


async def _component_label(session: AsyncSession, decision: StagedDecision) -> str | None:
    piece = await session.scalar(
        select(KnowledgePiece).where(KnowledgePiece.id == decision.id, *registered_pieces())
    )
    if piece is None:
        return None
    named = decision.craft or decision.family
    scope = "every page" if named is None else f"the page of {named}"
    return cut_label(f"Remove {piece.title} ({piece.label}) from {scope}")


async def _component_id(session: AsyncSession, label: str) -> uuid.UUID | None:
    return await session.scalar(
        select(KnowledgePiece.id).where(KnowledgePiece.label == label, *registered_pieces())
    )


async def _remove_component(
    session: AsyncSession, decision: StagedDecision, reviewer: User, now: datetime
) -> Carried:
    piece = await session.scalar(
        select(KnowledgePiece).where(KnowledgePiece.id == decision.id, *registered_pieces()).with_for_update()
    )
    if piece is None:
        raise InvalidInput(NO_ITEM.format(kind="component", id=decision.id))
    page = await _named_page(session, decision)
    retired = await take_off_pages(session, reviewer, piece, page=page, reason=decision.reason, now=now)
    if page is None:
        return Carried(REMOVED_EVERYWHERE.format(label=retired.label), retired.owners)
    return Carried(REMOVED_FROM.format(label=retired.label, page=page.name), retired.owners)


async def _named_page(session: AsyncSession, decision: StagedDecision) -> WorkSubject | None:
    if decision.family is not None:
        return await subject_by_key(session, CATEGORY, decision.family)
    if decision.craft is not None:
        return await craft_subject(session, decision.craft)
    return None


PUBLISHED_KINDS: Mapping[str, PublishedKind] = MappingProxyType(
    {
        COMPONENTS: PublishedKind(
            label=_component_label, find=_component_id, actions=MappingProxyType({REMOVE: _remove_component})
        ),
    }
)
