from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.core.roles import ROLE_RANK, is_uncapped
from app.models import AppSetting

MONTHLY_CEILING_USD = "AI_MONTHLY_CEILING_USD"
MEDIA_CAP_USD = "AI_MEDIA_CAP_USD"
ROLE_DAILY_USD = "AI_ROLE_DAILY_USD"
DEGRADE_AT_FRACTION = "AI_DEGRADE_AT_FRACTION"
ANSWER_CAP_USD = "AI_ANSWER_CAP_USD"
MODEL_PRICES = "AI_MODEL_PRICES"
SIGN_UP_MODE = "SIGN_UP_MODE"
DOMAIN_ALLOWLIST = "DOMAIN_ALLOWLIST"
VOICE_TRANSPORT = "voice.transport"
VOICE_MAX_LIVE_SESSIONS = "voice.max_live_sessions"
VOICE_VOICE_ID = "voice.voice_id"
BUDGET_FIELDS: dict[str, str] = {
    "monthlyCeilingUsd": MONTHLY_CEILING_USD,
    "mediaCapUsd": MEDIA_CAP_USD,
    "roleDailyUsd": ROLE_DAILY_USD,
    "degradeAtFraction": DEGRADE_AT_FRACTION,
    "answerCapUsd": ANSWER_CAP_USD,
    "signUpMode": SIGN_UP_MODE,
    "domainAllowlist": DOMAIN_ALLOWLIST,
}

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
    ANSWER_CAP_USD: {"BASIC": 0.25, "DETAILED": 0.5, "EXPERT": 1.0},
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
        "answerCapUsd": values[ANSWER_CAP_USD],
        "signUpMode": values[SIGN_UP_MODE],
        "domainAllowlist": values[DOMAIN_ALLOWLIST],
    }


def budget_changes(update: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    changes = {BUDGET_FIELDS[name]: value for name, value in update.items() if name in BUDGET_FIELDS}
    if ROLE_DAILY_USD in changes:
        _check_role_caps(changes[ROLE_DAILY_USD])
    if ANSWER_CAP_USD in changes:
        changes[ANSWER_CAP_USD] = {**current[ANSWER_CAP_USD], **changes[ANSWER_CAP_USD]}
    if DOMAIN_ALLOWLIST in changes:
        changes[DOMAIN_ALLOWLIST] = sorted(
            {d.strip().lower() for d in changes[DOMAIN_ALLOWLIST] if d.strip()}
        )
    media = changes.get(MEDIA_CAP_USD, current[MEDIA_CAP_USD])
    if media > changes.get(MONTHLY_CEILING_USD, current[MONTHLY_CEILING_USD]):
        raise InvalidInput("The media cap can't exceed the monthly ceiling.")
    return changes


def _check_role_caps(caps: Mapping[str, Any]) -> None:
    unknown = set(caps) - set(ROLE_RANK)
    if unknown:
        raise InvalidInput(f"Unknown roles: {', '.join(sorted(unknown))}")
    if any(is_uncapped(role) and cap is not None for role, cap in caps.items()):
        raise InvalidInput("Master Admins have no caps.")
