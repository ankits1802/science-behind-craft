import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.db import get_engine
from app.models import AppSetting, QuotaPolicy, RoutePolicy

from ..migration_scripts import migration

pytestmark = pytest.mark.db

STEP = migration("0029_unlimited_ai_use")
EARLIER_CAPS: dict[str, Any] = {
    "AI_MONTHLY_CEILING_USD": 800.0,
    "AI_MEDIA_CAP_USD": 150.0,
    "AI_ROLE_DAILY_USD": {"STUDENT": 0.5, "ADMIN": 10.0, "MASTER_ADMIN": None},
    "AI_DEGRADE_AT_FRACTION": 0.8,
    "AI_ANSWER_CAP_USD": {"BASIC": 0.25, "DETAILED": 1.0, "EXPERT": 2.5},
}
UPSERT = text(
    'INSERT INTO "AppSetting" (key, value) VALUES (:key, CAST(:value AS jsonb)) '
    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
)


@pytest.fixture
async def connection() -> AsyncIterator[AsyncConnection]:
    async with get_engine().connect() as opened:
        transaction = await opened.begin()
        try:
            yield opened
        finally:
            await transaction.rollback()


async def capped(connection: AsyncConnection) -> None:
    for key, value in EARLIER_CAPS.items():
        await connection.execute(UPSERT, {"key": key, "value": json.dumps(value)})
    await connection.execute(update(QuotaPolicy).values(perDay=5, perMonth=100))
    await connection.execute(update(RoutePolicy).values(maxOutputTokens=4096))


async def state(connection: AsyncConnection) -> tuple[int, int, int, int]:
    caps = await connection.scalar(
        select(func.count()).select_from(AppSetting).where(AppSetting.key.in_(STEP.CAP_SETTINGS))
    )
    quotas = await connection.scalar(
        select(func.count())
        .select_from(QuotaPolicy)
        .where(QuotaPolicy.perDay.is_not(None) | QuotaPolicy.perMonth.is_not(None))
    )
    routes = await connection.scalar(
        select(func.count()).select_from(RoutePolicy).where(RoutePolicy.maxOutputTokens.is_not(None))
    )
    others = await connection.scalar(
        select(func.count()).select_from(AppSetting).where(AppSetting.key.not_in(STEP.CAP_SETTINGS))
    )
    return int(caps or 0), int(quotas or 0), int(routes or 0), int(others or 0)


async def run_step(connection: AsyncConnection) -> None:
    for statement in STEP.UPGRADE_STATEMENTS:
        await connection.execute(text(statement))


async def test_the_step_lifts_every_stored_cap_and_a_second_run_changes_nothing(
    connection: AsyncConnection,
) -> None:
    await capped(connection)
    before = await state(connection)
    assert before[0] == len(EARLIER_CAPS) and before[1] > 0 and before[2] > 0
    await run_step(connection)
    once = await state(connection)
    await run_step(connection)
    twice = await state(connection)
    assert once[:3] == (0, 0, 0) and twice == once
    assert once[3] == before[3]
