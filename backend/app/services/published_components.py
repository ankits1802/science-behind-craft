from __future__ import annotations

import uuid
from datetime import datetime
from types import MappingProxyType
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import KnowledgePiece, User
from app.research.component_specs_general_delivery import DELIVERED_KEY, DeliveredUnit, UnitKey
from app.research.page_revalidation import PageOwners
from app.research.published_edits import ComponentEdit
from app.research.staged_reviews import EDIT, REMOVE, StagedDecision

from . import audit
from .component_library_applies import registered_pieces
from .component_lifecycle import PIECE_TARGET, piece_owners, take_off_pages
from .component_proposals_register import cited_sources, content_hash
from .component_proposals_spec import checked_drawing
from .open_work_subjects import CATEGORY, WorkSubject, craft_subject, subject_by_key
from .published_kinds import NO_ITEM, Carried, Editable, PublishedKind, PublishedRef, checked_edit

__all__ = ["COMPONENT_EDITED", "PUBLISHED_COMPONENTS"]

COMPONENT_EDITED = "component.edited"
REMOVED_EVERYWHERE = "Removed: {label} is off every page that placed it, and kept in the record."
REMOVED_FROM = "Removed from {page}'s page: {label} stays on every other page that places it."
EDITED = (
    "Edited: {label} is drawn as changed on every page that places it, and the change is kept in the record."
)
NOT_DELIVERED = "{label} is drawn from its page's own records, so it has no delivered spec or units to edit."
NEW_FACTS = (
    "An edit cites only the facts {label} already rests on, and these are new: {ids}. To cite other facts, "
    "propose a replacement that names replaces {label}."
)
UNITS: TypeAdapter[dict[str, DeliveredUnit]] = TypeAdapter(dict[UnitKey, DeliveredUnit])
TEXT_FIELDS = ("title", "description")


async def _piece(session: AsyncSession, piece_id: uuid.UUID, *, lock: bool = False) -> KnowledgePiece | None:
    query = select(KnowledgePiece).where(KnowledgePiece.id == piece_id, *registered_pieces())
    return await session.scalar(
        query.with_for_update().execution_options(populate_existing=True) if lock else query
    )


async def _name(session: AsyncSession, ref: PublishedRef) -> str | None:
    piece = await _piece(session, ref.id)
    return None if piece is None else f"{piece.title} ({piece.label})"


async def _id_of(session: AsyncSession, label: str) -> uuid.UUID | None:
    return await session.scalar(
        select(KnowledgePiece.id).where(KnowledgePiece.label == label, *registered_pieces())
    )


def _current(piece: KnowledgePiece) -> dict[str, Any]:
    delivered = (piece.payload or {}).get(DELIVERED_KEY) or {}
    return {
        "title": piece.title,
        "description": piece.description,
        "spec": delivered.get("spec"),
        "units": delivered.get("units"),
    }


async def _editable(session: AsyncSession, ref: PublishedRef) -> Editable | None:
    piece = await _piece(session, ref.id)
    return None if piece is None else Editable(_current(piece), ComponentEdit)


async def _remove(session: AsyncSession, decision: StagedDecision, reviewer: User, now: datetime) -> Carried:
    piece = await _piece(session, decision.id, lock=True)
    if piece is None:
        raise InvalidInput(NO_ITEM.format(kind="component", id=decision.id))
    page = await _named_page(session, decision)
    retired = await take_off_pages(session, reviewer, piece, page=page, reason=decision.reason, now=now)
    marks = (retired.label,)
    if page is None:
        return Carried(REMOVED_EVERYWHERE.format(label=retired.label), retired.owners, marks)
    message = REMOVED_FROM.format(label=retired.label, page=page.name)
    return Carried(message, retired.owners, marks, changed=_only(page))


def _only(page: WorkSubject) -> PageOwners:
    return PageOwners(categories=(page.slug,)) if page.kind == CATEGORY else PageOwners(crafts=(page.slug,))


async def _named_page(session: AsyncSession, decision: StagedDecision) -> WorkSubject | None:
    if decision.family is not None:
        return await subject_by_key(session, CATEGORY, decision.family)
    if decision.craft is not None:
        return await craft_subject(session, decision.craft)
    return None


async def _edit(session: AsyncSession, decision: StagedDecision, reviewer: User, _now: datetime) -> Carried:
    piece = await _piece(session, decision.id, lock=True)
    if piece is None:
        raise InvalidInput(NO_ITEM.format(kind="component", id=decision.id))
    before = _current(piece)
    fields = checked_edit(decision, Editable(before, ComponentEdit))
    if "spec" in fields or "units" in fields:
        await _redrawn(session, piece, fields)
    for name in TEXT_FIELDS:
        if name in fields:
            setattr(piece, name, fields[name])
    piece.contentHash = content_hash(_described(piece))
    await audit.record(
        session,
        action=COMPONENT_EDITED,
        actor=reviewer,
        target_type=PIECE_TARGET,
        target_id=piece.id,
        detail={
            "label": piece.label,
            "before": {name: before[name] for name in fields},
            "reason": decision.reason,
        },
    )
    await session.flush()
    owners = await piece_owners(session, piece)
    return Carried(EDITED.format(label=piece.label), owners, (str(piece.label),))


async def _redrawn(session: AsyncSession, piece: KnowledgePiece, fields: dict[str, Any]) -> None:
    delivered = (piece.payload or {}).get(DELIVERED_KEY)
    if delivered is None:
        raise InvalidInput(NOT_DELIVERED.format(label=piece.label))
    spec = fields.get("spec", delivered.get("spec")) or {}
    units = UNITS.validate_python(fields.get("units", delivered.get("units")) or {})
    checked = await checked_drawing(session, (piece.kind, spec, units))
    held = set(piece.claimIds)
    new = [str(claim) for claim in checked.claim_ids if claim not in held]
    if new:
        raise InvalidInput(NEW_FACTS.format(label=piece.label, ids=", ".join(new)))
    piece.payload = {**piece.payload, DELIVERED_KEY: {"spec": checked.spec, "units": checked.units}}
    if checked.claim_ids:
        piece.claimIds = list(checked.claim_ids)
        piece.sourceIds = await cited_sources(session, piece.claimIds) or piece.sourceIds


def _described(piece: KnowledgePiece) -> dict[str, Any]:
    return {
        "label": piece.label,
        "kind": piece.kind,
        "title": piece.title,
        "description": piece.description,
        "fields": list(piece.fields),
        "payload": piece.payload,
        "claimIds": [str(claim) for claim in piece.claimIds],
    }


PUBLISHED_COMPONENTS = PublishedKind(
    noun="component",
    name=_name,
    actions=MappingProxyType({REMOVE: _remove, EDIT: _edit}),
    find=_id_of,
    editable=_editable,
)
