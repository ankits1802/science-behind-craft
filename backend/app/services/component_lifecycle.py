from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput, Refused
from app.models import ComponentProposal, KnowledgePiece, KnowledgePieceSubject, KnowledgePieceUnlink, User
from app.research.page_proposals import ACCEPTED, WITHDRAWAL, PartReport
from app.research.page_revalidation import PageOwners

from . import audit
from .component_layout_swaps import swap_in_layouts
from .component_library_applies import APPLIED_PIECE, applies_to, registered_pieces
from .component_retirers import may_retire, proposal_of
from .open_work_subjects import CATEGORY, WorkSubject
from .page_revalidation import claim_owners, craft_owners, merged_owners

__all__ = [
    "NOT_REGISTERED",
    "PIECE_TARGET",
    "REMOVED_ACTION",
    "REPLACED_ACTION",
    "Retired",
    "check_replacement",
    "live_piece",
    "piece_owners",
    "proposal_of",
    "retirable_piece",
    "retire_replaced",
    "take_off_pages",
    "withdraw_registered",
    "withdrawn_owners",
]

REMOVED_ACTION = "component.removed"
REPLACED_ACTION = "component.replaced"
PIECE_TARGET = "KnowledgePiece"
APPROVED = "APPROVED"
WITHDRAWN = "WITHDRAWN"
NOT_RETIRING = "not_yours"
NOT_REGISTERED = "No registered component has the label {label}; list_components gives the labels."
NOT_YOURS = "Only the proposer of {label}, a steward of its craft or an Admin may take it off its pages or replace it."
NOT_ON_PAGE = "{label} is not on {page}'s page, so there is nothing to take off it."
OFF_ALREADY = "{label} is off {page}'s page already."


@dataclass(frozen=True)
class Retired:
    piece_id: uuid.UUID
    label: str
    owners: PageOwners


async def live_piece(session: AsyncSession, label: str, *, lock: bool = False) -> KnowledgePiece:
    query = select(KnowledgePiece).where(KnowledgePiece.label == label, *registered_pieces())
    if lock:
        query = query.with_for_update()
    piece = await session.scalar(query)
    if piece is None:
        raise InvalidInput(NOT_REGISTERED.format(label=label))
    return piece


async def retirable_piece(
    session: AsyncSession, user: User, label: str, *, lock: bool = False
) -> KnowledgePiece:
    piece = await live_piece(session, label, lock=lock)
    if not await may_retire(session, user, piece):
        raise Refused(NOT_RETIRING, NOT_YOURS.format(label=label))
    return piece


async def withdraw_registered(
    session: AsyncSession, user: User, label: str, *, reason: str | None, now: datetime
) -> Retired:
    piece = await live_piece(session, label, lock=True)
    return await take_off_pages(session, user, piece, page=None, reason=reason, now=now)


async def take_off_pages(
    session: AsyncSession,
    actor: User,
    piece: KnowledgePiece,
    *,
    page: WorkSubject | None,
    reason: str | None,
    now: datetime,
) -> Retired:
    if not await may_retire(session, actor, piece):
        raise Refused(NOT_RETIRING, NOT_YOURS.format(label=piece.label))
    if page is None:
        owners = await _hidden(session, actor, piece, now)
    else:
        owners = await _unlinked(session, actor, piece, page, reason)
    await audit.record(
        session,
        action=REMOVED_ACTION,
        actor=actor,
        target_type=PIECE_TARGET,
        target_id=piece.id,
        detail={
            "label": piece.label,
            "page": None if page is None else f"{page.kind}:{page.slug}",
            "reason": reason,
            "proposal": None if proposal_of(piece) is None else str(proposal_of(piece)),
        },
    )
    return Retired(piece.id, str(piece.label), owners)


async def check_replacement(session: AsyncSession, user: User, label: str | None) -> None:
    if label is not None:
        await retirable_piece(session, user, label)


async def retire_replaced(session: AsyncSession, row: ComponentProposal, piece_id: uuid.UUID) -> int:
    if row.replacesLabel is None:
        return 0
    old = await session.scalar(
        select(KnowledgePiece)
        .where(KnowledgePiece.label == row.replacesLabel, *registered_pieces())
        .with_for_update()
    )
    if old is None:
        return 0
    old.supersededById = piece_id
    await session.flush()
    actor = None if row.reviewedById is None else await session.get(User, row.reviewedById)
    swapped = await swap_in_layouts(session, row.replacesLabel, row.label, actor=actor)
    await audit.record(
        session,
        action=REPLACED_ACTION,
        actor=actor,
        target_type=PIECE_TARGET,
        target_id=old.id,
        detail={"label": old.label, "by": row.label, "proposal": str(row.id), "layouts": swapped},
    )
    return swapped


async def piece_owners(session: AsyncSession, piece: KnowledgePiece) -> PageOwners:
    keyed = await session.scalars(
        select(KnowledgePieceSubject.craftId).where(
            KnowledgePieceSubject.pieceId == piece.id, KnowledgePieceSubject.craftId.is_not(None)
        )
    )
    crafts = {craft for craft in keyed.all() if craft is not None}
    if piece.craftId is not None:
        crafts.add(piece.craftId)
    return merged_owners(
        await craft_owners(session, crafts), await claim_owners(session, list(piece.claimIds))
    )


async def withdrawn_owners(session: AsyncSession, parts: Sequence[PartReport]) -> PageOwners:
    ids = [uuid.UUID(p.id) for p in parts if p.part == WITHDRAWAL and p.outcome == ACCEPTED and p.id]
    if not ids:
        return PageOwners()
    pieces = await session.scalars(select(KnowledgePiece).where(KnowledgePiece.id.in_(ids)))
    return merged_owners(*[await piece_owners(session, piece) for piece in pieces.all()])


async def _hidden(session: AsyncSession, actor: User, piece: KnowledgePiece, now: datetime) -> PageOwners:
    piece.hiddenAt, piece.hiddenById = now, actor.id
    proposal_id = proposal_of(piece)
    if proposal_id is not None:
        await session.execute(
            update(ComponentProposal)
            .where(
                ComponentProposal.id == proposal_id,
                ComponentProposal.proposerId == actor.id,
                ComponentProposal.status == APPROVED,
            )
            .values(status=WITHDRAWN)
        )
    await session.flush()
    return await piece_owners(session, piece)


async def _unlinked(
    session: AsyncSession, actor: User, piece: KnowledgePiece, page: WorkSubject, reason: str | None
) -> PageOwners:
    category = page.kind == CATEGORY
    if not category and not await _applies(session, piece.id, page.id):
        raise InvalidInput(NOT_ON_PAGE.format(label=piece.label, page=page.name))
    unlink = KnowledgePieceUnlink(
        pieceId=piece.id,
        craftId=None if category else page.id,
        categoryId=page.id if category else None,
        unlinkedById=actor.id,
        reason=reason,
    )
    try:
        async with session.begin_nested():
            session.add(unlink)
    except IntegrityError:
        raise InvalidInput(OFF_ALREADY.format(label=piece.label, page=page.name)) from None
    return PageOwners(categories=(page.slug,)) if category else await craft_owners(session, [page.id])


async def _applies(session: AsyncSession, piece_id: uuid.UUID, craft_id: uuid.UUID) -> bool:
    applying = applies_to([craft_id]).subquery()
    found = await session.scalar(
        select(applying.c[APPLIED_PIECE]).where(applying.c[APPLIED_PIECE] == piece_id)
    )
    return found is not None
