from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.craft_master_loader import ACTIVE
from app.models import Craft, CraftCategory, CuratedCategory, CuratedCraft
from app.research.chapter_keys import DISCIPLINE_CHAPTERS
from app.research.craft_parts import Focal
from app.research.page_layout import HERO_CHAPTER, PICTURE_ROLES, PageLayoutEntry, picture_label

from .curated_category_index import stored_category_page
from .curated_index import IndexPicture, stored_curated_page
from .open_work_subjects import CATEGORY, WorkSubject, is_family, subject_by_key
from .page_layouts import layout_of, store_layout

__all__ = [
    "LEADING_ROLES",
    "LayoutBackfill",
    "backfill_page_layouts",
    "curated_pictures",
    "picture_entries",
    "picture_placement",
]

LEADING_ROLES = frozenset({"HERO", "OPENER"})
STAGE_CHAPTER = DISCIPLINE_CHAPTERS["PROCESS"]
STAGE_ROLE = "FIGURE"
LOOSE_ROLE = "PLATE"
HERO = "HERO"
FAMILY, CRAFT = "family", "craft"


@dataclass
class LayoutBackfill:
    written: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"written": self.written, "kept": self.kept}


def picture_placement(picture: IndexPicture) -> tuple[str, str]:
    if picture.placement is not None:
        role = PICTURE_ROLES[picture.placement.role]
        return (HERO_CHAPTER if role == HERO else picture.placement.chapter), role
    if picture.stage_key is not None:
        return STAGE_CHAPTER, STAGE_ROLE
    return HERO_CHAPTER, LOOSE_ROLE


def picture_entries(slug: str, pictures: Sequence[IndexPicture]) -> list[PageLayoutEntry]:
    placed = [(picture, *picture_placement(picture)) for picture in pictures]
    leading_first = sorted(placed, key=lambda item: item[2] not in LEADING_ROLES)
    orders: Counter[str] = Counter()
    entries: list[PageLayoutEntry] = []
    for picture, chapter, role in leading_first:
        orders[chapter] += 1
        focal = picture.focal
        entries.append(
            PageLayoutEntry(
                ref=picture_label(slug, picture.key),
                chapter=chapter,
                order=orders[chapter],
                role=role,
                crop=Focal(x=focal.x, y=focal.y, width=focal.width, height=focal.height) if focal else None,
            )
        )
    return entries


async def curated_pictures(session: AsyncSession, subject: WorkSubject) -> list[IndexPicture]:
    if subject.kind == CATEGORY:
        page = await session.scalar(
            select(CuratedCategory.page).where(CuratedCategory.categoryId == subject.id)
        )
        category = stored_category_page(subject.id, page)
        return list(category.pictures) if category is not None else []
    page = await session.scalar(select(CuratedCraft.page).where(CuratedCraft.craftId == subject.id))
    curated = stored_curated_page(subject.id, page)
    return list(curated.pictures) if curated is not None else []


async def backfill_page_layouts(session: AsyncSession) -> LayoutBackfill:
    report = LayoutBackfill()
    for subject in await _curated_subjects(session):
        named = f"{subject.kind}:{subject.slug}"
        if await layout_of(session, subject) is not None:
            report.kept.append(named)
            continue
        entries = picture_entries(subject.slug, await curated_pictures(session, subject))
        if entries:
            await store_layout(session, subject, entries, actor=None)
            report.written.append(named)
    return report


async def _curated_subjects(session: AsyncSession) -> list[WorkSubject]:
    crafts = (
        await session.execute(
            select(Craft.slug, Craft.isCatchAll, Craft.stateOfPractice)
            .join(CuratedCraft, CuratedCraft.craftId == Craft.id)
            .where(Craft.status == ACTIVE)
            .order_by(Craft.slug)
        )
    ).all()
    categories = (
        await session.scalars(
            select(CraftCategory.slug)
            .join(CuratedCategory, CuratedCategory.categoryId == CraftCategory.id)
            .order_by(CraftCategory.sortOrder)
        )
    ).all()
    found = [
        await subject_by_key(session, FAMILY if is_family(bool(catch_all), practice or ()) else CRAFT, slug)
        for slug, catch_all, practice in crafts
    ]
    return [*found, *[await subject_by_key(session, CATEGORY, slug) for slug in categories]]
