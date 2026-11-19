from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput, Refused
from app.models import AuditLog, PageLayout as LayoutRow, User
from app.research.page_layout import LayoutWrite
from app.services.page_layouts import LAYOUT_WRITTEN, page_layout, write_layout
from app.services.page_layouts_backfill import backfill_page_layouts
from app.services.static_pages import static_pages

from .page_documents_seed import (
    ADMIN,
    BARE_SLUG,
    CATEGORY_SLUG,
    CRAFT,
    CRAFT_SLUG,
    FAMILY_SLUG,
    PICTURE,
    seed,
)
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

HERO = {"ref": PICTURE, "chapter": "glance", "order": 1, "role": "HERO", "caption": "A cloth held up"}


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        yield opened


def written(base: int, *entries: dict[str, object]) -> LayoutWrite:
    return LayoutWrite.model_validate({"baseVersion": base, "entries": list(entries)})


async def test_an_admin_writes_versions_each_built_on_the_last_and_each_is_audited(
    session: AsyncSession,
) -> None:
    admin = await session.get(User, ADMIN)
    assert await page_layout(session, "craft", CRAFT_SLUG) is None
    first = await write_layout(session, "craft", CRAFT_SLUG, written(0, HERO), actor=admin)
    assert (first.version, first.subject_kind, first.entries[0].caption) == (1, "craft", "A cloth held up")
    with pytest.raises(Refused, match="at version 1, not 0"):
        await write_layout(session, "craft", CRAFT_SLUG, written(0), actor=admin)
    second = await write_layout(session, "craft", CRAFT_SLUG, written(1), actor=admin)
    assert second.version == 2
    assert (await page_layout(session, "craft", CRAFT_SLUG)).entries == []
    rows = (
        await session.scalars(select(LayoutRow).where(LayoutRow.craftId == CRAFT).order_by(LayoutRow.version))
    ).all()
    assert [(row.version, row.writtenByKind, row.writtenById) for row in rows] == [
        (1, "USER", ADMIN),
        (2, "USER", ADMIN),
    ]
    assert rows[0].entries == [HERO]
    audits = (
        await session.scalars(
            select(AuditLog).where(AuditLog.action == LAYOUT_WRITTEN, AuditLog.actorId == ADMIN)
        )
    ).all()
    assert sorted(audit.detail["version"] for audit in audits) == [1, 2]
    assert {audit.detail["subjectSlug"] for audit in audits} == {CRAFT_SLUG}


async def test_a_category_and_a_family_each_keep_their_own_layout(session: AsyncSession) -> None:
    admin = await session.get(User, ADMIN)
    entry = {"ref": "h-overview", "chapter": "glance", "order": 1, "role": "BODY"}
    await write_layout(session, "category", CATEGORY_SLUG, written(0, entry), actor=admin)
    family = await write_layout(session, "family", FAMILY_SLUG, written(0, entry), actor=admin)
    assert (family.subject_kind, family.version) == ("family", 1)
    category = await page_layout(session, "category", CATEGORY_SLUG)
    assert category is not None and (category.subject_kind, category.version) == ("category", 1)
    assert await page_layout(session, "craft", CRAFT_SLUG) is None


async def test_a_page_asked_for_as_the_wrong_kind_or_an_unknown_slug_is_refused(
    session: AsyncSession,
) -> None:
    with pytest.raises(InvalidInput, match="is a family, not a craft"):
        await page_layout(session, "craft", FAMILY_SLUG)
    with pytest.raises(InvalidInput, match="No category has the slug"):
        await page_layout(session, "category", "No-Such-Category-Here")


async def test_the_backfill_turns_curated_pictures_into_a_first_layout_once(session: AsyncSession) -> None:
    report = await backfill_page_layouts(session)
    assert f"craft:{CRAFT_SLUG}" in report.written
    stored = await page_layout(session, "craft", CRAFT_SLUG)
    assert stored is not None
    assert [(e.ref, e.chapter, e.order, e.role) for e in stored.entries] == [(PICTURE, "glance", 1, "HERO")]
    assert stored.entries[0].crop is not None
    assert (stored.entries[0].crop.x, stored.entries[0].crop.height) == (0.1, 0.6)
    row = await session.scalar(select(LayoutRow).where(LayoutRow.craftId == CRAFT))
    assert (row.writtenByKind, row.writtenById) == ("SYSTEM", None)
    again = await backfill_page_layouts(session)
    assert f"craft:{CRAFT_SLUG}" in again.kept and f"craft:{CRAFT_SLUG}" not in again.written


async def test_the_static_page_list_holds_every_craft_with_a_published_section(session: AsyncSession) -> None:
    listed = await static_pages(session)
    assert {CRAFT_SLUG, FAMILY_SLUG} <= set(listed.crafts)
    assert BARE_SLUG not in listed.crafts
    assert CATEGORY_SLUG in listed.categories
