from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require
from app.core.roles import Capability
from app.models import User
from app.schemas.admin import ManagedSecretSetIn
from app.services import audit, managed_secrets, two_factor

router = APIRouter(prefix="/secrets", tags=["secrets"])

TWO_FACTOR_REQUIRED_HEADER = "X-Two-Factor-Required"
STEP_UP_DETAIL = "Enter the code from your authenticator app to change keys."

key_manager = require(Capability.MANAGE_KEYS)


def _require_managed(key: str) -> str:
    if not managed_secrets.is_managed(key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That key isn't one that can be managed here.")
    return key


async def require_step_up(session: AsyncSession, user: User, code: str | None) -> None:
    if not user.twoFactorEnabled:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Turn on two-step verification to change keys.",
            {"X-Two-Factor-Setup-Required": "1"},
        )
    if not code or not await two_factor.step_up(session, user, code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, STEP_UP_DETAIL, {TWO_FACTOR_REQUIRED_HEADER: "1"})


@router.get("")
async def list_secrets(
    _: User = Depends(key_manager), session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    return await managed_secrets.list_managed_secrets(session)


@router.put("/{key}")
async def set_secret(
    key: str,
    payload: ManagedSecretSetIn,
    actor: User = Depends(key_manager),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _require_managed(key)
    value = payload.value.strip()
    if not value:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Enter a value, or clear the saved one.")
    await require_step_up(session, actor, payload.twoFactorCode)
    await audit.record(session, action="secrets.set", actor=actor, target_type="ManagedSecret", target_id=key)
    return await managed_secrets.set_secret(session, key, value, actor.id)


@router.delete("/{key}")
async def clear_secret(
    key: str,
    actor: User = Depends(key_manager),
    session: AsyncSession = Depends(get_session),
    x_two_factor_code: str | None = Header(default=None, max_length=64),
) -> dict[str, Any]:
    _require_managed(key)
    await require_step_up(session, actor, x_two_factor_code)
    await audit.record(
        session, action="secrets.cleared", actor=actor, target_type="ManagedSecret", target_id=key
    )
    return await managed_secrets.delete_secret(session, key)


@router.post("/{key}/test")
async def test_secret(
    key: str, actor: User = Depends(key_manager), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    _require_managed(key)
    result = await managed_secrets.test_secret(session, key)
    await audit.record(
        session,
        action="secrets.tested",
        actor=actor,
        target_type="ManagedSecret",
        target_id=key,
        detail={"status": result["lastStatus"]},
    )
    await session.commit()
    return result
