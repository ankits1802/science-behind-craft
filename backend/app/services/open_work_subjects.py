from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.data.craft_master_loader import ACTIVE, ALL_INDIA
from app.models import Craft, CraftCategory, CraftSubCategory
from app.research.category_page import category_path
from app.research.open_work import SUBJECT_KINDS, TaskSubject

__all__ = ["CATEGORY", "WorkSubject", "is_family", "subject_by_key", "work_subjects"]

CRAFT, FAMILY, CATEGORY = SUBJECT_KINDS
GI = "GI"
UNKNOWN = "No {kind} has the slug {slug}; find_crafts gives the slugs of crafts and families."
WRONG_KIND = "{slug} is a {found}, not a {kind}; filter by {found}."


@dataclass(frozen=True)
class WorkSubject:
    id: uuid.UUID
    kind: str
    slug: str
    name: str
    gi: bool

    def task_subject(self, site: str) -> TaskSubject:
        path = category_path(self.slug) if self.kind == CATEGORY else f"/crafts/{self.slug}"
        return TaskSubject(kind=self.kind, slug=self.slug, name=self.name, page_url=f"{site}{path}")


async def work_subjects(session: AsyncSession, subject: tuple[str, str] | None) -> list[WorkSubject]:
    if subject is None:
        return [*await _crafts(session), *await _categories(session)]
    kind, slug = subject
    if kind == CATEGORY:
        category = await _category(session, slug)
        members = await _crafts(session, CraftSubCategory.categoryId == category.id)
        return [category, *members]
    found = await _craft(session, slug, kind)
    if kind == CRAFT:
        return [found]
    row = await session.scalar(select(Craft.subCategoryId).where(Craft.id == found.id))
    members = [] if row is None else await _crafts(session, Craft.subCategoryId == row, Craft.id != found.id)
    return [found, *members]


async def subject_by_key(session: AsyncSession, kind: str, slug: str) -> WorkSubject:
    if kind == CATEGORY:
        return await _category(session, slug)
    return await _craft(session, slug, kind)


def is_family(catch_all: bool, practice: Sequence[str]) -> bool:
    return catch_all or tuple(practice) == (ALL_INDIA,)


async def _crafts(session: AsyncSession, *conditions: ColumnElement[bool]) -> list[WorkSubject]:
    rows = await session.execute(
        select(Craft.id, Craft.slug, Craft.name, Craft.giStatus, Craft.isCatchAll, Craft.stateOfPractice)
        .outerjoin(CraftSubCategory, CraftSubCategory.id == Craft.subCategoryId)
        .where(Craft.status == ACTIVE, *conditions)
        .order_by(Craft.slug)
    )
    return [_craft_subject(row) for row in rows.all()]


async def _craft(session: AsyncSession, slug: str, kind: str) -> WorkSubject:
    rows = await _crafts(session, Craft.slug == slug)
    if not rows:
        raise InvalidInput(UNKNOWN.format(kind=kind, slug=slug))
    found = rows[0]
    if found.kind != kind:
        raise InvalidInput(WRONG_KIND.format(slug=slug, found=found.kind, kind=kind))
    return found


async def _categories(session: AsyncSession) -> list[WorkSubject]:
    rows = await session.execute(
        select(CraftCategory.id, CraftCategory.slug, CraftCategory.name).order_by(CraftCategory.sortOrder)
    )
    return [WorkSubject(row.id, CATEGORY, row.slug, row.name, gi=False) for row in rows.all()]


async def _category(session: AsyncSession, slug: str) -> WorkSubject:
    row = (
        await session.execute(
            select(CraftCategory.id, CraftCategory.slug, CraftCategory.name).where(CraftCategory.slug == slug)
        )
    ).first()
    if row is None:
        raise InvalidInput(f"No category has the slug {slug}.")
    return WorkSubject(row.id, CATEGORY, row.slug, row.name, gi=False)


def _craft_subject(row: Any) -> WorkSubject:
    kind = FAMILY if is_family(bool(row.isCatchAll), row.stateOfPractice or ()) else CRAFT
    return WorkSubject(row.id, kind, row.slug, row.name, gi=row.giStatus == GI)
