from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Craft, CraftCategory, PageLayout as LayoutRow
from app.research.page_layout import PageLayoutEntry

from .open_work_subjects import CATEGORY, WorkSubject
from .page_layouts import layout_of, store_layout

__all__ = ["swap_in_layouts", "swapped_entries"]

CRAFT = "craft"


async def swap_in_layouts(session: AsyncSession, old: str, new: str, *, actor: Any) -> int:
    rows = await session.execute(
        select(LayoutRow.craftId, LayoutRow.categoryId)
        .where(LayoutRow.entries.contains([{"ref": old}]))
        .distinct()
    )
    written = 0
    for craft_id, category_id in rows.all():
        subject = await _subject(session, craft_id, category_id)
        layout = None if subject is None else await layout_of(session, subject)
        if subject is None or layout is None or layout.entry(old) is None:
            continue
        await store_layout(session, subject, swapped_entries(layout.entries, old, new), actor=actor)
        written += 1
    return written


def swapped_entries(entries: Sequence[PageLayoutEntry], old: str, new: str) -> list[PageLayoutEntry]:
    if any(entry.ref == new for entry in entries):
        return [entry for entry in entries if entry.ref != old]
    return [entry.model_copy(update={"ref": new}) if entry.ref == old else entry for entry in entries]


async def _subject(
    session: AsyncSession, craft_id: uuid.UUID | None, category_id: uuid.UUID | None
) -> WorkSubject | None:
    if category_id is not None:
        category = await session.get(CraftCategory, category_id)
        if category is None:
            return None
        return WorkSubject(id=category.id, kind=CATEGORY, slug=category.slug, name=category.name, gi=False)
    craft = None if craft_id is None else await session.get(Craft, craft_id)
    if craft is None:
        return None
    return WorkSubject(id=craft.id, kind=CRAFT, slug=craft.slug, name=craft.name, gi=False)
