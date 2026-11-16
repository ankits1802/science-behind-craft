import math
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import AdminDistrict, AdminState, Craft, CraftAlias, CraftLocation
from app.research.crafts import CraftQuery
from app.services.craft_resolver import (
    CraftIndexStore,
    DatabaseCraftResolver,
    fill_descriptor_embeddings,
    load_index,
)

from ..craft_fixtures import HALF, FixedEmbedder, unit

pytestmark = pytest.mark.db

PLAIN = uuid.uuid5(uuid.NAMESPACE_URL, "test-craft/Qorvane-Ikat")
LOCATED = uuid.uuid5(uuid.NAMESPACE_URL, "test-craft/Qorvane-Weave")
RETIRED = uuid.uuid5(uuid.NAMESPACE_URL, "test-craft/Old-Qorvane")
BARE = uuid.uuid5(uuid.NAMESPACE_URL, "test-craft/Qorvane-Twill")
STATE_LGD, DISTRICT_LGD = 990001, 990002

QUERY_VECTOR = unit(1.0)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            await _seed(session)
            yield session
            await session.close()
        finally:
            await transaction.rollback()


async def _seed(session: AsyncSession) -> None:
    session.add(AdminState(lgd=STATE_LGD, name="Zqland"))
    await session.flush()
    session.add(AdminDistrict(lgd=DISTRICT_LGD, stateLgd=STATE_LGD, name="Vexdistrict"))
    session.add_all(
        [
            Craft(id=PLAIN, slug="Qorvane-Ikat", name="Qorvane Ikat", descriptorEmbedding=unit(HALF, HALF)),
            Craft(id=LOCATED, slug="Qorvane-Weave", name="Qorvane Weave", descriptorEmbedding=unit(1.0)),
            Craft(id=BARE, slug="Qorvane-Twill", name="Qorvane Twill"),
        ]
    )
    await session.flush()
    session.add(
        Craft(id=RETIRED, slug="Old-Qorvane", name="Old Qorvane", status="MERGED", mergedIntoId=LOCATED)
    )
    session.add_all(
        [
            CraftAlias(craftId=PLAIN, alias="Qorvane", aliasNorm="qorvane", source="CURATED"),
            CraftAlias(craftId=LOCATED, alias="Qorvane", aliasNorm="qorvane", source="CURATED"),
            CraftAlias(craftId=BARE, alias="Qtwill", aliasNorm="qtwill", source="CURATED"),
            CraftLocation(
                craftId=LOCATED, precision="DISTRICT", districtLgd=DISTRICT_LGD, stateLgd=STATE_LGD
            ),
        ]
    )
    await session.flush()


def resolver(session: AsyncSession, embed: FixedEmbedder) -> DatabaseCraftResolver:
    return DatabaseCraftResolver(session, store=CraftIndexStore(), embed=embed)


async def test_a_district_name_from_the_location_table_settles_a_shared_alias(session: AsyncSession) -> None:
    embed = FixedEmbedder()
    found = await resolver(session, embed).resolve(CraftQuery(text="qorvane from Vexdistrict"))
    assert found.status == "RESOLVED"
    assert [(c.craft.slug, c.score) for c in found.candidates][:2] == [
        ("Qorvane-Weave", 0.976),
        ("Qorvane-Ikat", 0.776),
    ]
    assert ("PLACE", "Vexdistrict") in [(r.kind, r.matched) for r in found.candidates[0].reasons]
    assert embed.calls == []


async def test_a_merged_row_redirects_to_its_target(session: AsyncSession) -> None:
    found = await resolver(session, FixedEmbedder()).resolve(CraftQuery(text="Old Qorvane"))
    assert found.craft is not None and found.craft.slug == "Qorvane-Weave"
    assert found.candidates[0].reasons[0].kind == "MERGED_REDIRECT"


async def test_semantic_neighbours_come_from_pgvector(session: AsyncSession) -> None:
    index = await load_index(session)
    assert index.embedded >= 2
    embed = FixedEmbedder()
    found = await resolver(session, embed).resolve(CraftQuery(text="zzqx yyqv"))
    assert embed.calls == [["zzqx yyqv"]]
    scores = {c.craft.slug: c.score for c in found.candidates}
    assert scores["Qorvane-Weave"] == pytest.approx(0.8, abs=1e-5)
    assert scores["Qorvane-Ikat"] == pytest.approx(0.8 / math.sqrt(2), abs=1e-5)
    assert found.status == "AMBIGUOUS"


async def test_filling_descriptors_embeds_names_and_aliases(session: AsyncSession) -> None:
    embed = FixedEmbedder()
    filled = await fill_descriptor_embeddings(session, embed, batch_size=500)
    sent = [text for call in embed.calls for text in call]
    assert filled == len(sent)
    assert "Qorvane Twill; Qtwill" in sent
    stored = await session.scalar(select(Craft.descriptorEmbedding).where(Craft.id == BARE))
    assert stored is not None and list(stored) == QUERY_VECTOR
