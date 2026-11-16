import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.data.craft_master_loader import load_master, seed_plan, seed_uuid
from app.models import Craft, CraftAlias
from app.services.craft_seed import seed_crafts
from app.services.portal_craft_feed import parse_feed
from app.services.portal_craft_sync import sync_feeds
from tests.portal_sync.fixtures import SYNCED_AT, craft

pytestmark = pytest.mark.db

CRAFT_TABLES = ("CraftAlias", "CraftSpelling", "Craft", "CraftCode", "CraftSubCategory", "CraftCategory")
NEW = "KV-Sync-Test-Craft"
OLD = "KV-Sync-Test-Old"


def feeds(*, designer_lists_new: bool = True) -> list[Any]:
    master = load_master()[0]
    category = {
        "id": "cat",
        "slug": master.category_slug,
        "name": master.category,
        "subCategories": [{"id": "sub", "slug": master.sub_category_slug, "name": master.sub_category}],
    }
    designer_crafts = [craft("d1", master.slug, "Portal Name X", sub="sub", aliases=["Portal Alias One"])]
    if designer_lists_new:
        designer_crafts += [
            craft("d2", NEW, "KV Sync Test Craft", sub="sub"),
            craft("d3", OLD, "KV Sync Test Old", sub="sub", status="MERGED", merged_into="d2"),
        ]
    designer = {
        "schemaVersion": 1,
        "portal": "DESIGNER",
        "generatedAt": SYNCED_AT,
        "categories": [category],
        "crafts": designer_crafts,
    }
    field = {
        "schemaVersion": 1,
        "portal": "FIELD_REPOSITORY",
        "generatedAt": SYNCED_AT,
        "categories": [category],
        "crafts": [
            craft("f1", NEW, "KV Sync Test Craft", sub="sub", status="LEGACY", aliases=["Field Alias"])
        ],
    }
    return [parse_feed(designer, portal="DESIGNER"), parse_feed(field, portal="FIELD_REPOSITORY")]


async def _row(session: AsyncSession, slug: str) -> Any:
    query = select(Craft).where(Craft.slug == slug).execution_options(populate_existing=True)
    return (await session.execute(query)).scalar_one()


async def _count(session: AsyncSession, model: Any) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def _aliases(session: AsyncSession, craft_id: uuid.UUID) -> set[tuple[str, str]]:
    rows = await session.execute(
        select(CraftAlias.alias, CraftAlias.source).where(CraftAlias.craftId == craft_id)
    )
    return set(rows.all())


@asynccontextmanager
async def seeded_session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            quoted = ", ".join(f'"{name}"' for name in CRAFT_TABLES)
            await session.execute(text(f"TRUNCATE {quoted} CASCADE"))
            await seed_crafts(session, seed_plan())
            yield session
            await session.close()
        finally:
            await transaction.rollback()


async def _check_first_sync(session: AsyncSession) -> uuid.UUID:
    master = load_master()[0]
    first = await sync_feeds(session, tuple(feeds()), synced_at=SYNCED_AT)
    assert (first.crafts_created, first.crafts_merged) == (2, 1)
    new = await _row(session, NEW)
    assert str(new.id) == seed_uuid("c", NEW)
    assert new.status == "ACTIVE"
    assert list(new.extraMetadata["portalSources"]) == ["DESIGNER", "FIELD_REPOSITORY"]
    assert new.extraMetadata["portalOrigin"] == "DESIGNER"
    assert ("Field Alias", "FR_SYNC") in await _aliases(session, new.id)
    old = await _row(session, OLD)
    assert (old.status, old.mergedIntoId) == ("MERGED", new.id)
    kept = await _row(session, master.slug)
    assert (kept.name, kept.status) == (master.name, "ACTIVE")
    assert kept.extraMetadata["masterSeed"]
    assert kept.extraMetadata["portalSources"]["DESIGNER"]["name"] == "Portal Name X"
    expected = {("Portal Name X", "DR_SYNC"), ("Portal Alias One", "DR_SYNC")}
    assert expected <= await _aliases(session, kept.id)
    return new.id


async def test_portal_crafts_are_upserted_beside_the_master_list() -> None:
    async with seeded_session() as session:
        new_id = await _check_first_sync(session)

        crafts, aliases = await _count(session, Craft), await _count(session, CraftAlias)
        await sync_feeds(session, tuple(feeds()), synced_at=SYNCED_AT)
        assert (await _count(session, Craft), await _count(session, CraftAlias)) == (crafts, aliases)
        assert (await _row(session, NEW)).id == new_id

        await sync_feeds(session, tuple(feeds(designer_lists_new=False)), synced_at=SYNCED_AT)
        assert (await _row(session, NEW)).status == "LEGACY"
        gone = await _row(session, OLD)
        assert (gone.status, gone.mergedIntoId, gone.extraMetadata["portalSources"]) == ("LEGACY", None, {})
