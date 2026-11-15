from typing import Any

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.data.craft_master_loader import seed_plan
from app.models import Craft, CraftAlias, CraftCategory, CraftCode, CraftSpelling, CraftSubCategory
from app.services.craft_seed import seed_crafts

pytestmark = pytest.mark.db

CRAFT_TABLES = ("CraftAlias", "CraftSpelling", "Craft", "CraftCode", "CraftSubCategory", "CraftCategory")


async def _counts(session: AsyncSession) -> dict[str, int]:
    models = {
        "categories": CraftCategory,
        "subCategories": CraftSubCategory,
        "crafts": Craft,
        "codes": CraftCode,
        "spellings": CraftSpelling,
        "aliases": CraftAlias,
    }
    return {
        key: (await session.execute(select(func.count()).select_from(model))).scalar_one()
        for key, model in models.items()
    }


async def _identity(session: AsyncSession) -> dict[str, Any]:
    crafts = dict((await session.execute(select(Craft.slug, Craft.id))).all())
    aliases = set((await session.execute(select(CraftAlias.craftId, CraftAlias.aliasNorm))).all())
    return {"crafts": crafts, "aliases": aliases}


async def test_seed_crafts_is_idempotent_on_an_empty_database() -> None:
    plan = seed_plan()
    expected = {key: len(rows) for key, rows in plan.items()}
    assert expected["crafts"] == 455
    assert expected["codes"] == 50

    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            quoted = ", ".join(f'"{name}"' for name in CRAFT_TABLES)
            await session.execute(text(f"TRUNCATE {quoted} CASCADE"))
            assert set((await _counts(session)).values()) == {0}

            first = await seed_crafts(session, plan)
            assert first == expected
            after_first = await _counts(session)
            assert after_first == expected
            identity = await _identity(session)

            second = await seed_crafts(session, plan)
            assert second == expected
            assert await _counts(session) == expected
            assert await _identity(session) == identity

            slugs = {row["slug"] for row in plan["crafts"]}
            assert set(identity["crafts"]) == slugs
            active = (
                await session.execute(select(func.count()).select_from(Craft).where(Craft.status == "ACTIVE"))
            ).scalar_one()
            assert active == sum(1 for row in plan["crafts"] if row.get("status", "ACTIVE") == "ACTIVE")
            await session.close()
        finally:
            await transaction.rollback()
