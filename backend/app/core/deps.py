import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from app.core.config import get_settings
from app.core.db import get_session
from app.core.logging import set_log_user
from app.core.roles import (
    ROLE_RANK,
    Capability,
    can,
    capabilities_of,
    has_rank,
    is_master_admin,
    requires_two_factor,
    role_rank,
    role_value,
)
from app.core.security import TOKEN_VERSION_CLAIM, decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

SIGN_IN_DETAIL = "Sign in to continue."
SESSION_ENDED_DETAIL = "This session is no longer valid. Sign in again."

PASSWORD_CHANGE_REQUIRED_HEADER = "X-Password-Change-Required"
PASSWORD_CHANGE_REQUIRED_DETAIL = "Choose a new password to continue."

TWO_FACTOR_SETUP_REQUIRED_HEADER = "X-Two-Factor-Setup-Required"
TWO_FACTOR_SETUP_REQUIRED_DETAIL = "Turn on two-step verification to continue."

API_PREFIX = "/api"

PASSWORD_CHANGE_ALLOWED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", f"{API_PREFIX}/auth/me"),
        ("GET", f"{API_PREFIX}/me"),
        ("POST", f"{API_PREFIX}/auth/change-password"),
        ("POST", f"{API_PREFIX}/auth/logout"),
    }
)

TWO_FACTOR_SETUP_ALLOWED_ROUTES: frozenset[tuple[str, str]] = PASSWORD_CHANGE_ALLOWED_ROUTES | frozenset(
    {
        ("GET", f"{API_PREFIX}/auth/two-factor"),
        ("POST", f"{API_PREFIX}/auth/two-factor/setup"),
        ("POST", f"{API_PREFIX}/auth/two-factor/setup/cancel"),
        ("POST", f"{API_PREFIX}/auth/two-factor/enable"),
    }
)


def is_configured_master_admin(user: Any) -> bool:
    address = str(getattr(user, "email", "") or "").strip().lower()
    configured = (get_settings().master_admin_email or "").strip().lower()
    return bool(address) and address == configured


def is_break_glass_master(user: Any) -> bool:
    return is_master_admin(user) or is_configured_master_admin(user)


def password_change_pending(user: Any) -> bool:
    if not getattr(user, "mustChangePassword", False):
        return False
    if not getattr(user, "passwordHash", None):
        return False
    return not is_configured_master_admin(user)


def two_factor_setup_pending(user: Any) -> bool:
    return requires_two_factor(user) and not bool(getattr(user, "twoFactorEnabled", False))


def _route(connection: HTTPConnection) -> tuple[str, str]:
    method = str(connection.scope.get("method") or "").upper()
    path = str(connection.scope.get("path") or "")
    root = str(connection.scope.get("root_path") or "")
    if root and path.startswith(root):
        path = path[len(root) :] or "/"
    return method, path.rstrip("/") or "/"


def refuse_pending_steps(user: Any, connection: HTTPConnection) -> None:
    route = _route(connection)
    if password_change_pending(user) and route not in PASSWORD_CHANGE_ALLOWED_ROUTES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=PASSWORD_CHANGE_REQUIRED_DETAIL,
            headers={PASSWORD_CHANGE_REQUIRED_HEADER: "1"},
        )
    if two_factor_setup_pending(user) and route not in TWO_FACTOR_SETUP_ALLOWED_ROUTES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=TWO_FACTOR_SETUP_REQUIRED_DETAIL,
            headers={TWO_FACTOR_SETUP_REQUIRED_HEADER: "1"},
        )


def token_matches_user(claims: dict[str, Any], user: Any) -> bool:
    if getattr(user, "deletedAt", None) is not None:
        return False
    if int(claims.get(TOKEN_VERSION_CLAIM, -1)) != int(getattr(user, "tokenVersion", 0) or 0):
        return False
    valid_from = getattr(user, "sessionsValidFrom", None)
    if valid_from is not None:
        issued = claims.get("iat")
        if not isinstance(issued, int | float) or issued < valid_from.timestamp():
            return False
    return True


async def user_from_token(session: AsyncSession, token: str) -> User:
    try:
        claims = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    try:
        user_id = uuid.UUID(str(claims.get("sub")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=SESSION_ENDED_DETAIL) from exc
    user = await session.get(User, user_id)
    if user is None or not token_matches_user(claims, user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=SESSION_ENDED_DETAIL)
    return user


async def get_current_user_any_step(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=SIGN_IN_DETAIL)
    user = await user_from_token(session, credentials.credentials)
    set_log_user(str(user.id))
    return user


async def get_current_user(
    connection: HTTPConnection,
    user: User = Depends(get_current_user_any_step),
) -> User:
    refuse_pending_steps(user, connection)
    return user


CAPABILITY_REFUSALS: dict[Capability, str] = {
    Capability.ASK_DEEP: "Deep research is for researchers and above.",
    Capability.GENERATE_VIDEO: "Video is for researchers and above.",
    Capability.MANAGE_ACCESS: "Managing who may sign in is for professors and the master admin.",
    Capability.LIST_USERS: "Managing users is for professors and the master admin.",
    Capability.CHANGE_ROLES: "Only the master admin can change roles.",
    Capability.DISABLE_USERS: "Only the master admin can suspend accounts.",
    Capability.MANAGE_KEYS: "Only the master admin can manage keys.",
    Capability.MANAGE_ROUTING: "Only the master admin can change routing.",
    Capability.VIEW_USAGE: "Only the master admin can see platform usage.",
}


def refusal_for(capability: Capability) -> str:
    return CAPABILITY_REFUSALS.get(capability, "Your role does not allow this.")


def require(capability: Capability) -> Callable[..., Coroutine[Any, Any, User]]:
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if not can(user, capability):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=refusal_for(capability))
        return user

    dependency.__name__ = f"require_{capability.value.lower()}"
    return dependency


async def require_master_admin(user: User = Depends(get_current_user)) -> User:
    if not is_master_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Master admin access required")
    return user


__all__ = [
    "ROLE_RANK",
    "Capability",
    "can",
    "capabilities_of",
    "get_current_user",
    "get_current_user_any_step",
    "has_rank",
    "is_break_glass_master",
    "is_configured_master_admin",
    "require",
    "require_master_admin",
    "role_rank",
    "role_value",
]
