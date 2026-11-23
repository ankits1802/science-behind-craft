import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import Chunk, Source

pytestmark = pytest.mark.db

SOURCE = uuid.uuid5(uuid.NAMESPACE_URL, "test-chunk-kinds/source")


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            session.add(Source(id=SOURCE, kind="FIELD_TESTIMONY", title="Field interview, test visit"))
            await session.flush()
            yield session
            await session.close()
        finally:
            await transaction.rollback()


async def stored_kinds(session: AsyncSession) -> list[tuple[int, str, str]]:
    rows = await session.execute(
        select(Chunk.ordinal, Chunk.acl, Chunk.kind).where(Chunk.sourceId == SOURCE).order_by(Chunk.ordinal)
    )
    return [(ordinal, acl, kind) for ordinal, acl, kind in rows.tuples()]


async def test_no_trigger_marks_windows_and_no_chunk_is_left_signed_in(session: AsyncSession) -> None:
    triggers = await session.execute(
        text("SELECT tgname FROM pg_trigger WHERE tgrelid = to_regclass('\"Chunk\"') AND NOT tgisinternal")
    )
    assert "Chunk_kind_window_mark" not in triggers.scalars().all()
    signed_in = await session.execute(
        text("""SELECT count(*) FROM "Chunk" WHERE "acl"::text = 'SIGNED_IN'""")
    )
    assert signed_in.scalar_one() == 0
    rows = [{"sourceId": SOURCE, "ordinal": 0, "text": "Researcher: How is it made?", "acl": "PUBLIC"}]
    await session.execute(insert(Chunk.__table__).values(rows))
    assert await stored_kinds(session) == [(0, "PUBLIC", "PASSAGE")]


async def test_this_release_writes_a_public_window_and_its_kind_stands(session: AsyncSession) -> None:
    session.add_all(
        [
            Chunk(sourceId=SOURCE, ordinal=0, text="We grind the alum with tamarind seed.", acl="PUBLIC"),
            Chunk(
                sourceId=SOURCE, ordinal=1, text="Researcher: How is it made?", acl="PUBLIC", kind="WINDOW"
            ),
        ]
    )
    await session.flush()
    assert await stored_kinds(session) == [(0, "PUBLIC", "PASSAGE"), (1, "PUBLIC", "WINDOW")]
