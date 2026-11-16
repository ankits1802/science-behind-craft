import time
import uuid
from datetime import UTC, datetime

import httpx

from app.core.db import session_scope
from app.core.security import hash_password
from app.models import AccessRoster, User
from app.services import two_factor

PASSWORD = "correct-horse-battery"


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"


def code(secret: str, steps_ahead: int = 0) -> str:
    return two_factor.current_totp(secret, time.time() + 30 * steps_ahead)


async def create_user(
    email: str, role: str, *, with_two_factor: bool = False, rostered: bool = True
) -> str | None:
    secret = two_factor.generate_secret() if with_two_factor else None
    async with session_scope() as session:
        session.add(
            User(
                email=email,
                name=email.split("@")[0],
                passwordHash=hash_password(PASSWORD),
                role=role,
                twoFactorEnabled=with_two_factor,
                twoFactorSecret=two_factor.encrypt_secret(secret) if secret else None,
                emailVerifiedAt=datetime.now(UTC),
            )
        )
        if rostered:
            session.add(AccessRoster(email=email, status="ACTIVE", admitRole=role))
    return secret


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(
    client: httpx.AsyncClient, email: str, secret: str | None = None, steps_ahead: int = 0
) -> str:
    response = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    body = response.json()
    if body.get("two_factor_required"):
        assert secret is not None
        verified = await client.post(
            "/api/auth/two-factor/verify",
            json={"challenge_token": body["challenge_token"], "code": code(secret, steps_ahead)},
        )
        assert verified.status_code == 200, verified.text
        body = verified.json()
    return body["accessToken"]
