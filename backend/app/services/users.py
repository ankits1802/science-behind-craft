from datetime import datetime
from typing import Any

from app.core.roles import ROLE_LABELS, capabilities_of, requires_two_factor, role_value
from app.models import User

SECRET_USER_FIELDS = frozenset(
    {
        "passwordHash",
        "twoFactorSecret",
        "twoFactorPendingSecret",
        "twoFactorRecoveryCodes",
        "twoFactorLastStep",
        "tokenVersion",
    }
)

PUBLIC_USER_FIELDS = (
    "email",
    "name",
    "avatarUrl",
    "role",
    "authProvider",
    "affiliation",
    "mustChangePassword",
    "twoFactorEnabled",
    "emailVerifiedAt",
    "firstLoginAt",
    "lastLoginAt",
    "passwordSetAt",
    "ageAttestedAt",
    "createdAt",
    "updatedAt",
)


def _plain(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize_user(user: User, *, access_status: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": str(user.id)}
    for field in PUBLIC_USER_FIELDS:
        payload[field] = _plain(getattr(user, field, None))
    payload["roleLabel"] = ROLE_LABELS.get(role_value(user), role_value(user))
    payload["hasPassword"] = user.passwordHash is not None
    payload["twoFactorRequired"] = requires_two_factor(user)
    payload["twoFactorSetupRequired"] = requires_two_factor(user) and not user.twoFactorEnabled
    payload["capabilities"] = capabilities_of(user)
    if access_status is not None:
        payload["accessStatus"] = access_status
        payload["isActive"] = user.deletedAt is None and access_status not in ("SUSPENDED", "REJECTED")
    return payload
