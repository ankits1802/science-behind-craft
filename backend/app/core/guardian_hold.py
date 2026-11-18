from __future__ import annotations

import uuid
from collections.abc import Collection
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import STUDENT, role_value
from app.models import ConsentRecord, StudentProfile
from app.models.enums import MINOR_AGE_BANDS

__all__ = [
    "GUARDIAN_CONSENT",
    "GUARDIAN_CONSENT_REQUIRED_DETAIL",
    "GUARDIAN_CONSENT_REQUIRED_HEADER",
    "GUARDIAN_HOLD_ALLOWED_ROUTES",
    "GUARDIAN_STATEMENT_VERSION",
    "confirmed_among",
    "guardian_confirmed",
    "guardian_hold_owed",
    "refuse_until_guardian_consent",
]

GUARDIAN_CONSENT = "GUARDIAN_CONSENT"
GUARDIAN_STATEMENT_VERSION = "2026-11-18"
GUARDIAN_CONSENT_REQUIRED_HEADER = "X-Guardian-Consent-Required"
GUARDIAN_CONSENT_REQUIRED_DETAIL = (
    "Your teacher needs to confirm that your parent or guardian agrees before you continue."
)
PROFILE_PREFIX = "/api/profile/me"
GUARDIAN_HOLD_ALLOWED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/auth/me"),
        ("GET", "/api/me"),
        ("GET", "/api/privacy/notice"),
        ("POST", "/api/auth/logout"),
    }
)
PROFILE_METHODS = frozenset({"GET", "PUT"})


def _allowed(route: tuple[str, str]) -> bool:
    method, path = route
    if route in GUARDIAN_HOLD_ALLOWED_ROUTES:
        return True
    in_profile = path == PROFILE_PREFIX or path.startswith(f"{PROFILE_PREFIX}/")
    return in_profile and method in PROFILE_METHODS


def _confirmation(user_id: uuid.UUID) -> Any:
    return exists().where(
        ConsentRecord.userId == user_id,
        ConsentRecord.kind == GUARDIAN_CONSENT,
        ConsentRecord.withdrawnAt.is_(None),
    )


async def guardian_confirmed(session: AsyncSession, user_id: uuid.UUID) -> bool:
    return bool(await session.scalar(select(_confirmation(user_id))))


async def confirmed_among(session: AsyncSession, user_ids: Collection[uuid.UUID]) -> set[uuid.UUID]:
    if not user_ids:
        return set()
    rows = await session.scalars(
        select(ConsentRecord.userId).where(
            ConsentRecord.userId.in_(list(user_ids)),
            ConsentRecord.kind == GUARDIAN_CONSENT,
            ConsentRecord.withdrawnAt.is_(None),
        )
    )
    return set(rows)


async def guardian_hold_owed(session: AsyncSession, user: Any) -> bool:
    if role_value(user) != STUDENT:
        return False
    held = (
        select(StudentProfile.userId)
        .where(
            StudentProfile.userId == user.id,
            StudentProfile.ageBand.in_(MINOR_AGE_BANDS),
            ~_confirmation(user.id),
        )
        .limit(1)
    )
    return await session.scalar(held) is not None


async def refuse_until_guardian_consent(session: AsyncSession, user: Any, route: tuple[str, str]) -> None:
    if role_value(user) != STUDENT or _allowed(route):
        return
    owed = await guardian_hold_owed(session, user)
    await session.commit()
    if owed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=GUARDIAN_CONSENT_REQUIRED_DETAIL,
            headers={GUARDIAN_CONSENT_REQUIRED_HEADER: "1"},
        )
