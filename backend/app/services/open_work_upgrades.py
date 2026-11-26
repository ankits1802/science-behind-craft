from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Subquery, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LayoutProposal, PageUpgrade

from .open_work_subjects import CATEGORY, WorkSubject
from .page_layout_proposals import APPROVED, PENDING

__all__ = ["approved_layouts", "open_upgrades", "same_page"]

Page = tuple[uuid.UUID | None, uuid.UUID | None]


def approved_layouts() -> Subquery:
    return (
        select(
            LayoutProposal.craftId,
            LayoutProposal.categoryId,
            func.max(LayoutProposal.layoutVersion).label("version"),
        )
        .where(LayoutProposal.status == APPROVED)
        .group_by(LayoutProposal.craftId, LayoutProposal.categoryId)
        .subquery()
    )


def same_page(page: Any, other: Any) -> ColumnElement[bool]:
    return or_(page.craftId == other.craftId, page.categoryId == other.categoryId)


async def open_upgrades(
    session: AsyncSession, subjects: Sequence[WorkSubject]
) -> dict[uuid.UUID, tuple[str, ...]]:
    by_key = {(subject.kind, subject.slug): subject for subject in subjects}
    raised = [
        (by_key[(row.subjectKind, row.subjectSlug)], row)
        for row in (await session.scalars(select(PageUpgrade))).all()
        if (row.subjectKind, row.subjectSlug) in by_key
    ]
    if not raised:
        return {}
    pages = [_page(subject) for subject, _ in raised]
    built = await _latest(session, pages, APPROVED, func.max(LayoutProposal.layoutVersion))
    waiting = await _latest(session, pages, PENDING, func.max(LayoutProposal.createdAt))
    return {
        subject.id: tuple(row.lines)
        for subject, row in raised
        if built.get(_page(subject)) == row.layoutVersion
        and not _rebuilding(waiting.get(_page(subject)), row)
    }


def _page(subject: WorkSubject) -> Page:
    return (None, subject.id) if subject.kind == CATEGORY else (subject.id, None)


async def _latest(
    session: AsyncSession, pages: Sequence[Page], status: str, latest: Any
) -> Mapping[Page, Any]:
    crafts = [owner for owner, _ in pages if owner is not None]
    categories = [owner for _, owner in pages if owner is not None]
    rows = await session.execute(
        select(LayoutProposal.craftId, LayoutProposal.categoryId, latest)
        .where(
            LayoutProposal.status == status,
            or_(LayoutProposal.craftId.in_(crafts), LayoutProposal.categoryId.in_(categories)),
        )
        .group_by(LayoutProposal.craftId, LayoutProposal.categoryId)
    )
    return {(craft, category): value for craft, category, value in rows.tuples().all()}


def _rebuilding(latest: datetime | None, row: PageUpgrade) -> bool:
    return latest is not None and latest >= row.raisedAt
