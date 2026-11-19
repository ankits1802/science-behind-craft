from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Refused
from app.models import PageLayout as LayoutRow
from app.research.category_page import category_path
from app.research.page_layout import LayoutWrite, PageLayout, PageLayoutEntry

from . import audit
from .open_work_subjects import CATEGORY, WorkSubject, subject_by_key

__all__ = [
    "LAYOUT_TARGET",
    "LAYOUT_WRITTEN",
    "STALE_LAYOUT",
    "layout_of",
    "page_layout",
    "store_layout",
    "subject_path",
    "write_layout",
]

LAYOUT_WRITTEN = "PAGE_LAYOUT_WRITTEN"
LAYOUT_TARGET = "PageLayout"
STALE_LAYOUT = "stale_layout"
STALE_DETAIL = (
    "The layout of {slug} is at version {current}, not {base}. Read it again and build on version {current}."
)
USER, SYSTEM = "USER", "SYSTEM"


def subject_path(subject: WorkSubject) -> str:
    return category_path(subject.slug) if subject.kind == CATEGORY else f"/crafts/{subject.slug}"


async def page_layout(session: AsyncSession, kind: str, slug: str) -> PageLayout | None:
    return await layout_of(session, await subject_by_key(session, kind, slug))


async def layout_of(session: AsyncSession, subject: WorkSubject) -> PageLayout | None:
    row = await session.scalar(
        select(LayoutRow).where(_of(subject)).order_by(LayoutRow.version.desc()).limit(1)
    )
    return None if row is None else _layout(subject, row)


async def write_layout(
    session: AsyncSession, kind: str, slug: str, written: LayoutWrite, *, actor: Any
) -> PageLayout:
    subject = await subject_by_key(session, kind, slug)
    current = await _latest_version(session, subject)
    if written.base_version != current:
        raise Refused(
            STALE_LAYOUT, STALE_DETAIL.format(slug=slug, current=current, base=written.base_version)
        )
    return await store_layout(session, subject, written.entries, actor=actor)


async def store_layout(
    session: AsyncSession, subject: WorkSubject, entries: Sequence[PageLayoutEntry], *, actor: Any
) -> PageLayout:
    version = await _latest_version(session, subject) + 1
    row = LayoutRow(
        craftId=None if subject.kind == CATEGORY else subject.id,
        categoryId=subject.id if subject.kind == CATEGORY else None,
        version=version,
        entries=[entry.model_dump(mode="json", by_alias=True, exclude_none=True) for entry in entries],
        writtenByKind=USER if actor is not None else SYSTEM,
        writtenById=getattr(actor, "id", None),
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError as raced:
        detail = STALE_DETAIL.format(slug=subject.slug, current=version, base=version - 1)
        raise Refused(STALE_LAYOUT, detail) from raced
    await audit.record(
        session,
        action=LAYOUT_WRITTEN,
        actor=actor,
        target_type=LAYOUT_TARGET,
        target_id=row.id,
        detail={
            "subjectKind": subject.kind,
            "subjectSlug": subject.slug,
            "version": version,
            "entries": len(entries),
        },
    )
    return _layout(subject, row)


async def _latest_version(session: AsyncSession, subject: WorkSubject) -> int:
    latest = await session.scalar(select(func.max(LayoutRow.version)).where(_of(subject)))
    return int(latest or 0)


def _of(subject: WorkSubject) -> ColumnElement[bool]:
    if subject.kind == CATEGORY:
        return LayoutRow.categoryId == subject.id
    return LayoutRow.craftId == subject.id


def _layout(subject: WorkSubject, row: LayoutRow) -> PageLayout:
    return PageLayout(
        subject_kind=subject.kind,
        subject_slug=subject.slug,
        version=row.version,
        entries=[PageLayoutEntry.model_validate(entry) for entry in row.entries],
    )
