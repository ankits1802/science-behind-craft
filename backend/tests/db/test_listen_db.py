import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_engine
from app.models import Answer, QuotaLedger, User
from app.providers.quota import LedgerEntry
from app.services.answer_store import EXPLAINER_PAYLOAD_KEY
from app.voice.listen_store import SqlListenStore

from ..contracts.golden import golden_json

pytestmark = pytest.mark.db

NOW = datetime.now(UTC).replace(microsecond=0)
Stores = tuple[SqlListenStore, AsyncSession]


@pytest.fixture
async def store() -> AsyncIterator[Stores]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            factory = async_sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            async with factory() as session:
                yield SqlListenStore(factory), session
        finally:
            await transaction.rollback()


async def reader(session: AsyncSession, role: str = "STUDENT") -> User:
    user = User(
        id=uuid.uuid4(), name="Listen Reader", email=f"listen-{uuid.uuid4().hex[:8]}@example.com", role=role
    )
    session.add(user)
    await session.commit()
    return user


async def answer(
    session: AsyncSession, user: User, payload: dict | None, answer_id: uuid.UUID | None = None
) -> uuid.UUID:
    answer_id = answer_id or uuid.uuid4()
    session.add(
        Answer(id=answer_id, userId=user.id, question="How is Ajrakh made?", mode="HYBRID", payload=payload)
    )
    await session.commit()
    return answer_id


def seconds(user: User, units: int, key: str) -> LedgerEntry:
    return LedgerEntry(
        user_id=user.id, resource="VOICE_SECONDS", units=units, key=key, ref_type="Answer", ref_id="a"
    )


async def test_the_reader_s_own_stored_explainer_is_read_back(store: Stores) -> None:
    listen, session = store
    user, other = await reader(session), await reader(session)
    answer_id = uuid.uuid4()
    document = {**golden_json("explainer.document.golden.json"), "answerId": str(answer_id)}
    await answer(session, user, {EXPLAINER_PAYLOAD_KEY: document}, answer_id)
    found = await listen.explainer(answer_id, user.id)
    assert found is not None and [s.id for s in found.sections] == ["s1", "s2", "s3"]
    assert await listen.explainer(answer_id, other.id) is None


async def test_an_answer_without_an_explainer_has_nothing_to_read(store: Stores) -> None:
    listen, session = store
    user = await reader(session)
    voice_turn = await answer(session, user, {"channel": "VOICE", "sentences": []})
    nothing = await answer(session, user, None)
    assert await listen.explainer(voice_turn, user.id) is None
    assert await listen.explainer(nothing, user.id) is None


@pytest.mark.usefixtures("allowances_an_owner_might_set")
async def test_a_hold_is_written_only_while_seconds_are_left(store: Stores) -> None:
    listen, session = store
    user = await reader(session)
    hold = await listen.hold(seconds(user, 590, f"listen:{uuid.uuid4()}:hold"), NOW)
    assert (hold.held, hold.remaining_after, hold.refused) == (590, 10, False)
    refused = await listen.hold(seconds(user, 11, f"listen:{uuid.uuid4()}:hold"), NOW)
    assert refused.refused and refused.remaining_after == 10
    await listen.record(seconds(user, -90, f"listen-refund:{uuid.uuid4()}"))
    units = await session.scalars(select(QuotaLedger.units).where(QuotaLedger.userId == user.id))
    assert sorted(int(unit) for unit in units) == [-90, 590]


@pytest.mark.parametrize("role", ["STUDENT", "ARTISAN", "RESEARCHER", "PROFESSOR", "ADMIN"])
async def test_by_default_every_role_holds_any_length_and_the_seconds_are_still_written(
    store: Stores, role: str
) -> None:
    listen, session = store
    user = await reader(session, role)
    first = await listen.hold(seconds(user, 100_000, f"listen:{uuid.uuid4()}:hold"), NOW)
    second = await listen.hold(seconds(user, 100_000, f"listen:{uuid.uuid4()}:hold"), NOW)
    assert [(hold.held, hold.remaining_after, hold.refused) for hold in (first, second)] == [
        (100_000, None, False),
        (100_000, None, False),
    ]
    units = await session.scalars(select(QuotaLedger.units).where(QuotaLedger.userId == user.id))
    assert sorted(int(unit) for unit in units) == [100_000, 100_000]


async def test_a_master_admin_holds_any_length(store: Stores) -> None:
    listen, session = store
    owner = await reader(session, "MASTER_ADMIN")
    hold = await listen.hold(seconds(owner, 100_000, f"listen:{uuid.uuid4()}:hold"), NOW)
    assert (hold.held, hold.remaining_after, hold.refused) == (100_000, None, False)
