from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSetting

MONTHLY_CEILING_USD = "AI_MONTHLY_CEILING_USD"
MEDIA_CAP_USD = "AI_MEDIA_CAP_USD"
ROLE_DAILY_USD = "AI_ROLE_DAILY_USD"
DEGRADE_AT_FRACTION = "AI_DEGRADE_AT_FRACTION"
MODEL_PRICES = "AI_MODEL_PRICES"
SIGN_UP_MODE = "SIGN_UP_MODE"
DOMAIN_ALLOWLIST = "DOMAIN_ALLOWLIST"
VOICE_TRANSPORT = "voice.transport"
VOICE_MAX_LIVE_SESSIONS = "voice.max_live_sessions"
VOICE_VOICE_ID = "voice.voice_id"

DEFAULTS: dict[str, Any] = {
    MONTHLY_CEILING_USD: 800.0,
    MEDIA_CAP_USD: 150.0,
    ROLE_DAILY_USD: {
        "STUDENT": 0.5,
        "RESEARCHER": 3.0,
        "PROFESSOR": 5.0,
        "ADMIN": 10.0,
        "MASTER_ADMIN": None,
    },
    DEGRADE_AT_FRACTION: 0.8,
    MODEL_PRICES: {},
    SIGN_UP_MODE: "ROSTER",
    DOMAIN_ALLOWLIST: [],
    VOICE_TRANSPORT: "RELAY",
    VOICE_MAX_LIVE_SESSIONS: 5,
    VOICE_VOICE_ID: "JBFqnCBsd6RMkjVDRZzb",
}


async def load_all(session: AsyncSession) -> dict[str, Any]:
    rows = (await session.execute(select(AppSetting))).scalars().all()
    values = dict(DEFAULTS)
    for row in rows:
        values[row.key] = row.value
    return values


async def get_value(session: AsyncSession, key: str) -> Any:
    row = (await session.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
    return row.value if row is not None else DEFAULTS.get(key)


async def set_value(session: AsyncSession, key: str, value: Any, updated_by_id: Any = None) -> None:
    await session.execute(
        insert(AppSetting)
        .values(key=key, value=value, updatedById=updated_by_id)
        .on_conflict_do_update(
            index_elements=[AppSetting.key], set_={"value": value, "updatedById": updated_by_id}
        )
    )


def public_view(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "monthlyCeilingUsd": values[MONTHLY_CEILING_USD],
        "mediaCapUsd": values[MEDIA_CAP_USD],
        "roleDailyUsd": values[ROLE_DAILY_USD],
        "degradeAtFraction": values[DEGRADE_AT_FRACTION],
        "signUpMode": values[SIGN_UP_MODE],
        "domainAllowlist": values[DOMAIN_ALLOWLIST],
    }
