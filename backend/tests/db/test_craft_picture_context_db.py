import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_engine
from app.data.craft_families import load_craft_families
from app.models import Craft, CraftAlias, CraftCategory, CraftLocation, CraftSubCategory
from app.services.craft_picture_context import craft_picture_context

pytestmark = pytest.mark.db

TEXTILES = "Textiles based Craft Category"
BLOCK_PRINTING = "Hand Block Printing"
KACHCHH_LGD, GUJARAT_LGD = 449, 24


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            factory = async_sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            async with factory() as opened:
                yield opened
        finally:
            await transaction.rollback()


async def printed_craft(session: AsyncSession) -> Craft:
    kind = await session.scalar(
        select(CraftSubCategory.id)
        .join(CraftCategory, CraftCategory.id == CraftSubCategory.categoryId)
        .where(CraftCategory.name == TEXTILES, CraftSubCategory.name == BLOCK_PRINTING)
    )
    assert kind is not None
    craft = Craft(
        id=uuid.uuid4(),
        name="Ajrakh of Dhamadka",
        localName="Ajrak",
        slug=f"Picture-World-{uuid.uuid4().hex[:8]}",
        subCategoryId=kind,
        stateOfOrigin=["Gujarat"],
        stateOfPractice=["All India"],
    )
    session.add(craft)
    await session.flush()
    session.add_all(craft_records(craft.id))
    await session.commit()
    return craft


def craft_records(craft_id: uuid.UUID) -> list[CraftAlias | CraftLocation]:
    return [
        CraftAlias(
            craftId=craft_id, alias="Sindhi Ajrak resist", aliasNorm="sindhi ajrak resist", source="CURATED"
        ),
        CraftAlias(
            craftId=craft_id,
            alias="Khatri print",
            aliasNorm="khatri print",
            source="CURATED",
            status="PROPOSED",
        ),
        CraftLocation(
            craftId=craft_id,
            precision="DISTRICT",
            districtLgd=KACHCHH_LGD,
            stateLgd=GUJARAT_LGD,
            placeLabel="Dhamadka River (Suran)",
            evidenceLevel="REVIEWED",
        ),
    ]


async def test_a_craft_s_world_is_its_names_its_places_and_its_family_s_words(session: AsyncSession) -> None:
    craft = await printed_craft(session)
    world = await craft_picture_context(session, craft.slug)
    textiles = load_craft_families().family("Textiles-Based-Craft-Category")
    assert textiles is not None
    named = {"ajrakh", "dhamadka", "ajrak", "sindhi", "gujarat", "suran", "kachchh"}
    assert world.words == named | set(textiles.picture_words)
    assert not world.named_in("All India Radio")
    assert not world.named_in("Khatri family portrait")


async def test_no_craft_or_an_unknown_one_holds_a_picture_to_every_family_s_words(
    session: AsyncSession,
) -> None:
    every = set(load_craft_families().picture_words)
    assert (await craft_picture_context(session, None)).words == every
    assert (await craft_picture_context(session, "No-Such-Craft-Anywhere")).words == every
