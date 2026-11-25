from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import (
    Claim,
    ClaimSource,
    Craft,
    CraftCategory,
    CraftGiRecord,
    CuratedCategoryClaim,
    CuratedClaim,
    Reaction,
    TermCraft,
    User,
)
from app.research.page_revalidation import PageOwners
from app.research.review_labels import cut_label
from app.research.staged_reviews import EDIT, REMOVE, StagedDecision
from app.research.structure_edits import EDITS, UNEDITED
from app.research.structure_proposals import (
    CATEGORY_SUBJECT,
    CONFLICT,
    CRAFT_SUBJECT,
    GI_RECORD,
    GLOSSARY_TERM,
    REACTION,
)
from app.research.structure_proposals_values import edited_check

from . import audit
from .open_work_subjects import CATEGORY
from .page_revalidation import craft_owners
from .published_kinds import (
    NO_ITEM,
    Carried,
    Editable,
    PublishedKind,
    PublishedLine,
    PublishedQuery,
    PublishedRef,
    checked_edit,
    ref_of,
)
from .published_structure_entries import (
    FoundEntry,
    checked_item,
    edited_page,
    entries_of,
    page_entries,
    without_entry,
)
from .structure_proposals_owner import StructureOwner, owner_page, store_owner_page
from .structure_proposals_page import OwnerPage, target_problem
from .structure_proposals_write import held_claims
from .term_glossary import term_id

__all__ = ["PUBLISHED_STRUCTURE", "STRUCTURE_EDITED", "STRUCTURE_REMOVED"]

STRUCTURE_REMOVED = "structure.removed"
STRUCTURE_EDITED = "structure.edited"
TARGET = "StructureEntry"
REMOVED = "Removed: {name} is off the page of {slug}, and the entry as it was and the reason are kept in the record."
EDITED = (
    "Edited: {name} reads as changed on the page of {slug}, and its earlier values are kept in the record."
)
SEVERAL = (
    "This fact holds up more than one entry of its page ({kinds}): name the one meant as entry, then stage it "
    "anew."
)
PAGE_NEEDED = "Name the craft, family or category whose page's structure entries to list."
UNSTATED = "Not edited: the {check} check refused it. {reasons}"
GI_COLUMNS = {
    "application_number": "applicationNumber",
    "certificate_number": "certificateNumber",
    "filed_on": "filedOn",
    "registered_on": "registeredOn",
    "journal_issue": "journalIssue",
    "proprietors": "proprietors",
    "authorised_user_count": "authorisedUserCount",
}


@dataclass(frozen=True)
class _Found:
    owner: StructureOwner
    entry: FoundEntry
    page: OwnerPage | None = None
    gi: CraftGiRecord | None = None


async def _claim_owner(session: AsyncSession, claim_id: uuid.UUID) -> StructureOwner | None:
    craft = (
        await session.execute(
            select(Craft.id, Craft.slug, Craft.name)
            .join(CuratedClaim, CuratedClaim.craftId == Craft.id)
            .where(CuratedClaim.claimId == claim_id)
        )
    ).first()
    if craft is not None:
        return StructureOwner(CRAFT_SUBJECT, craft.id, craft.slug, craft.name)
    category = (
        await session.execute(
            select(CraftCategory.id, CraftCategory.slug, CraftCategory.name)
            .join(CuratedCategoryClaim, CuratedCategoryClaim.categoryId == CraftCategory.id)
            .where(CuratedCategoryClaim.claimId == claim_id)
        )
    ).first()
    return (
        None
        if category is None
        else StructureOwner(CATEGORY_SUBJECT, category.id, category.slug, category.name)
    )


async def _gi_of(session: AsyncSession, claim_id: uuid.UUID, *, lock: bool) -> _Found | None:
    query = select(CraftGiRecord, Craft).join(Craft, Craft.id == CraftGiRecord.craftId)
    query = query.where(CraftGiRecord.claimIds.contains([claim_id]))
    found = (
        await session.execute(
            query.with_for_update(of=CraftGiRecord).execution_options(populate_existing=True)
            if lock
            else query
        )
    ).first()
    if found is None:
        return None
    record, craft = found
    owner = StructureOwner(CRAFT_SUBJECT, craft.id, craft.slug, craft.name)
    current = {name: getattr(record, column) for name, column in GI_COLUMNS.items()}
    entry = FoundEntry(
        GI_RECORD,
        craft.slug,
        cut_label(f"GI record of {craft.name}"),
        tuple(record.claimIds),
        current=current,
    )
    return _Found(owner, entry, gi=record)


async def _found(session: AsyncSession, ref: PublishedRef, *, lock: bool = False) -> _Found | None:
    found: list[_Found] = []
    if ref.entry in (None, GI_RECORD):
        gi = await _gi_of(session, ref.id, lock=lock)
        found += [] if gi is None else [gi]
    owner = await _claim_owner(session, ref.id) if ref.entry != GI_RECORD else None
    page = None if owner is None else await owner_page(session, owner, lock=lock)
    if owner is not None and page is not None:
        found += [_Found(owner, entry, page) for entry in entries_of(page, ref.id, ref.entry)]
    if len(found) > 1:
        raise InvalidInput(SEVERAL.format(kinds=", ".join(each.entry.kind for each in found)))
    return found[0] if found else None


async def _name(session: AsyncSession, ref: PublishedRef) -> str | None:
    found = await _found(session, ref)
    return None if found is None else found.entry.name


def _editable_of(entry: FoundEntry) -> Editable:
    return Editable(entry.current, EDITS.get(entry.kind), UNEDITED.get(entry.kind))


async def _editable(session: AsyncSession, ref: PublishedRef) -> Editable | None:
    found = await _found(session, ref)
    return None if found is None else _editable_of(found.entry)


async def _held(session: AsyncSession, decision: StagedDecision) -> _Found:
    found = await _found(session, ref_of(decision), lock=True)
    if found is None:
        raise InvalidInput(NO_ITEM.format(kind="structure entry", id=decision.id))
    return found


async def _remove(session: AsyncSession, decision: StagedDecision, reviewer: User, _now: datetime) -> Carried:
    found = await _held(session, decision)
    owner, entry = found.owner, found.entry
    if found.gi is not None:
        await session.delete(found.gi)
    elif found.page is not None:
        await store_owner_page(session, owner, without_entry(found.page, entry))
        await _rows_without(session, owner, entry)
    await _audited(
        session, STRUCTURE_REMOVED, (reviewer, found), {"was": dict(entry.current), "reason": decision.reason}
    )
    return Carried(REMOVED.format(name=entry.name, slug=owner.slug), await _owners(session, owner))


async def _edit(session: AsyncSession, decision: StagedDecision, reviewer: User, _now: datetime) -> Carried:
    found = await _held(session, decision)
    owner, entry = found.owner, found.entry
    fields = checked_edit(decision, _editable_of(entry))
    item = checked_item(entry, fields)
    if found.gi is not None:
        await _refuse_unstated(session, entry, item)
        for name, value in fields.items():
            setattr(found.gi, GI_COLUMNS[name], value)
    elif found.page is not None:
        problem = target_problem(
            without_entry(found.page, entry), item, held=await held_claims(session, owner)
        )
        if problem is not None:
            raise InvalidInput(problem)
        await _refuse_unstated(session, entry, item)
        await store_owner_page(session, owner, edited_page(found.page, entry, fields))
        await _rows_edited(session, entry, fields)
    before = {name: entry.current.get(name) for name in fields}
    await _audited(
        session, STRUCTURE_EDITED, (reviewer, found), {"before": before, "reason": decision.reason}
    )
    return Carried(EDITED.format(name=entry.name, slug=owner.slug), await _owners(session, owner))


async def _refuse_unstated(session: AsyncSession, entry: FoundEntry, item: Any) -> None:
    quotes = await session.scalars(
        select(ClaimSource.quote)
        .where(ClaimSource.claimId.in_(list(entry.claim_ids)), ClaimSource.quote.is_not(None))
        .order_by(ClaimSource.createdAt, ClaimSource.id)
    )
    before = type(item).model_construct(**entry.fixed, **entry.current)
    check = edited_check(before, item, [str(quote) for quote in quotes.all()])
    if not check.passed:
        raise InvalidInput(UNSTATED.format(check=check.check, reasons=" ".join(check.reasons)))


async def _rows_without(session: AsyncSession, owner: StructureOwner, entry: FoundEntry) -> None:
    if entry.kind == REACTION and entry.reaction_id is not None:
        await session.execute(delete(Reaction).where(Reaction.id == entry.reaction_id))
    if entry.kind == GLOSSARY_TERM and entry.term_key is not None and not owner.is_category:
        await session.execute(
            delete(TermCraft).where(
                TermCraft.termId == term_id(entry.term_key), TermCraft.craftId == owner.id
            )
        )
    if entry.kind == CONFLICT:
        await _marked(session, entry, {"sourcesDiffer": False, "differsOn": None})


async def _rows_edited(session: AsyncSession, entry: FoundEntry, fields: dict[str, Any]) -> None:
    if entry.kind == CONFLICT and "about" in fields:
        await _marked(session, entry, {"differsOn": fields["about"]})


async def _marked(session: AsyncSession, entry: FoundEntry, values: dict[str, Any]) -> None:
    await session.execute(
        update(Claim).where(Claim.id.in_(list(entry.claim_ids)), Claim.differsOn == entry.key).values(values)
    )


async def _audited(
    session: AsyncSession, action: str, by: tuple[User, _Found], detail: dict[str, Any]
) -> None:
    reviewer, found = by
    await audit.record(
        session,
        action=action,
        actor=reviewer,
        target_type=TARGET,
        target_id=found.entry.claim_ids[0] if found.entry.claim_ids else None,
        detail={
            "page": f"{found.owner.kind}:{found.owner.slug}",
            "entry": found.entry.kind,
            "key": found.entry.key,
            **detail,
        },
    )
    await session.flush()


async def _owners(session: AsyncSession, owner: StructureOwner) -> PageOwners:
    if owner.is_category:
        return PageOwners(categories=(owner.slug,))
    return await craft_owners(session, [owner.id])


async def _listed(session: AsyncSession, query: PublishedQuery) -> list[PublishedLine]:
    if query.page is None:
        raise InvalidInput(PAGE_NEEDED)
    subject = query.page
    kind = CATEGORY_SUBJECT if subject.kind == CATEGORY else CRAFT_SUBJECT
    owner = StructureOwner(kind, subject.id, subject.slug, subject.name)
    page = await owner_page(session, owner, lock=False)
    entries = [] if page is None else page_entries(page)
    gi = None if owner.is_category else await session.get(CraftGiRecord, owner.id)
    if gi is not None and gi.claimIds:
        entries.append(
            FoundEntry(GI_RECORD, owner.slug, cut_label(f"GI record of {owner.name}"), tuple(gi.claimIds))
        )
    lines = [
        PublishedLine(entry.claim_ids[0], entry.name, entry.kind) for entry in entries if entry.claim_ids
    ]
    return lines[query.offset : query.offset + query.limit]


PUBLISHED_STRUCTURE = PublishedKind(
    noun="structure entry",
    name=_name,
    actions=MappingProxyType({REMOVE: _remove, EDIT: _edit}),
    listed=_listed,
    editable=_editable,
)
