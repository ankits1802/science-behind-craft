from __future__ import annotations

import uuid
from datetime import datetime
from types import MappingProxyType

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import AuditLog, Craft, CraftCategory, PageLayout as LayoutRow, User
from app.research.page_layout import PageLayoutEntry
from app.research.page_revalidation import PageOwners
from app.research.review_labels import cut_label
from app.research.staged_reviews import REMOVE, StagedDecision

from . import audit
from .open_work_subjects import CATEGORY, WorkSubject, craft_subject, subject_by_key
from .page_layouts import LAYOUT_TARGET, store_layout
from .page_revalidation import craft_owners
from .published_kinds import NO_ITEM, Carried, PublishedKind, PublishedLine, PublishedQuery, PublishedRef

__all__ = ["LAYOUT_REMOVED", "PUBLISHED_LAYOUTS"]

LAYOUT_REMOVED = "layout.removed"
BACK_TO = (
    "Removed: the page of {slug} goes back to its layout of version {version}, the latest earlier arrangement "
    "that is neither this one nor one a removal took off, written as version {written}; every version stays "
    "in the record."
)
BACK_TO_DEFAULT = (
    "Removed: the page of {slug} goes back to its default arrangement, because every earlier arrangement is "
    "this one or one a removal took off, written as version {written}; every version stays in the record."
)
NOT_CURRENT = (
    "Version {version} is no longer the page's layout; version {current} is. Stage its removal anew."
)
PAGE_NEEDED = "Name the page whose layout to list: a craft, family or category."


async def _row(session: AsyncSession, layout_id: uuid.UUID, *, lock: bool = False) -> LayoutRow | None:
    query = select(LayoutRow).where(LayoutRow.id == layout_id)
    return await session.scalar(
        query.with_for_update().execution_options(populate_existing=True) if lock else query
    )


async def _subject(session: AsyncSession, row: LayoutRow) -> WorkSubject | None:
    if row.categoryId is not None:
        slug = await session.scalar(select(CraftCategory.slug).where(CraftCategory.id == row.categoryId))
        return None if slug is None else await subject_by_key(session, CATEGORY, slug)
    slug = await session.scalar(select(Craft.slug).where(Craft.id == row.craftId))
    return None if slug is None else await craft_subject(session, slug)


def _same_page(row: LayoutRow) -> ColumnElement[bool]:
    if row.categoryId is not None:
        return LayoutRow.categoryId == row.categoryId
    return LayoutRow.craftId == row.craftId


async def _latest(session: AsyncSession, row: LayoutRow) -> int:
    return int(await session.scalar(select(func.max(LayoutRow.version)).where(_same_page(row))) or 0)


async def _name(session: AsyncSession, ref: PublishedRef) -> str | None:
    row = await _row(session, ref.id)
    subject = None if row is None else await _subject(session, row)
    if row is None or subject is None or row.version != await _latest(session, row):
        return None
    return cut_label(f"Layout version {row.version} of the page of {subject.slug}")


async def _remove(session: AsyncSession, decision: StagedDecision, reviewer: User, _now: datetime) -> Carried:
    row = await _row(session, decision.id, lock=True)
    subject = None if row is None else await _subject(session, row)
    if row is None or subject is None:
        raise InvalidInput(NO_ITEM.format(kind="layout", id=decision.id))
    current = await _latest(session, row)
    if row.version != current:
        raise InvalidInput(NOT_CURRENT.format(version=row.version, current=current))
    earlier = await _earlier(session, row)
    entries = [] if earlier is None else [PageLayoutEntry.model_validate(entry) for entry in earlier.entries]
    written = await store_layout(session, subject, entries, actor=reviewer)
    await audit.record(
        session,
        action=LAYOUT_REMOVED,
        actor=reviewer,
        target_type=LAYOUT_TARGET,
        target_id=row.id,
        detail={
            "page": f"{subject.kind}:{subject.slug}",
            "version": row.version,
            "restored": None if earlier is None else earlier.version,
            "reason": decision.reason,
        },
    )
    await session.flush()
    message = (
        BACK_TO_DEFAULT.format(slug=subject.slug, written=written.version)
        if earlier is None
        else BACK_TO.format(slug=subject.slug, version=earlier.version, written=written.version)
    )
    return Carried(message, await _owners(session, subject))


async def _earlier(session: AsyncSession, row: LayoutRow) -> LayoutRow | None:
    found = await session.scalars(
        select(LayoutRow)
        .where(_same_page(row), LayoutRow.version < row.version)
        .order_by(LayoutRow.version.desc())
    )
    earlier = list(found.all())
    taken_off = set(
        await session.scalars(
            select(AuditLog.targetId).where(
                AuditLog.action == LAYOUT_REMOVED,
                AuditLog.targetType == LAYOUT_TARGET,
                AuditLog.targetId.in_([str(each.id) for each in earlier]),
            )
        )
    )
    unwanted = [row.entries, *(each.entries for each in earlier if str(each.id) in taken_off)]
    return next((each for each in earlier if each.entries not in unwanted), None)


async def _owners(session: AsyncSession, subject: WorkSubject) -> PageOwners:
    if subject.kind == CATEGORY:
        return PageOwners(categories=(subject.slug,))
    return await craft_owners(session, [subject.id])


async def _listed(session: AsyncSession, query: PublishedQuery) -> list[PublishedLine]:
    if query.page is None:
        raise InvalidInput(PAGE_NEEDED)
    page = query.page
    of = LayoutRow.categoryId == page.id if page.kind == CATEGORY else LayoutRow.craftId == page.id
    row = await session.scalar(select(LayoutRow).where(of).order_by(LayoutRow.version.desc()).limit(1))
    if row is None or query.offset > 0:
        return []
    return [PublishedLine(row.id, cut_label(f"Layout version {row.version} of the page of {page.slug}"))]


PUBLISHED_LAYOUTS = PublishedKind(
    noun="layout", name=_name, actions=MappingProxyType({REMOVE: _remove}), listed=_listed
)
