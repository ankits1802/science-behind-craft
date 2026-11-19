from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Craft, CraftCategory, CraftPageSnapshot

from .craft_page_snapshots import OPEN

__all__ = ["STATIC_PAGES_SCHEMA_VERSION", "StaticPages", "static_pages"]

STATIC_PAGES_SCHEMA_VERSION = 1


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
    crafts = await session.scalars(
        select(Craft.slug)
        .join(CraftPageSnapshot, CraftPageSnapshot.craftId == Craft.id)
        .where(CraftPageSnapshot.variant == OPEN)
        .order_by(Craft.slug)
    )
    categories = await session.scalars(select(CraftCategory.slug).order_by(CraftCategory.sortOrder))
    return StaticPages(crafts=tuple(crafts), categories=tuple(categories))
