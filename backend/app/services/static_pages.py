from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArticleSection, Craft, CraftCategory, CraftPageSnapshot

from .craft_page_snapshots import OPEN
from .open_work_pages import monograph_layouts

__all__ = ["STATIC_PAGES_SCHEMA_VERSION", "StaticPages", "static_pages"]

STATIC_PAGES_SCHEMA_VERSION = 1
PUBLISHED = "PUBLISHED"


@dataclass(frozen=True)
class StaticPages:
    crafts: tuple[str, ...]
    categories: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": STATIC_PAGES_SCHEMA_VERSION,
            "crafts": list(self.crafts),
            "categories": list(self.categories),
        }


async def static_pages(session: AsyncSession) -> StaticPages:
    snapshotted = select(CraftPageSnapshot.craftId).where(CraftPageSnapshot.variant == OPEN)
    sectioned = select(ArticleSection.craftId).where(
        ArticleSection.craftId.is_not(None), ArticleSection.status == PUBLISHED
    )
    crafts = await session.scalars(
        select(Craft.slug)
        .where(
            or_(Craft.id.in_(snapshotted), Craft.id.in_(sectioned), Craft.slug.in_(list(monograph_layouts())))
        )
        .order_by(Craft.slug)
    )
    categories = await session.scalars(select(CraftCategory.slug).order_by(CraftCategory.sortOrder))
    return StaticPages(crafts=tuple(crafts), categories=tuple(categories))
