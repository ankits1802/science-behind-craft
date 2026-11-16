import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuthNonce

NONCE_MINUTES = 10
NONCE_MAX_LENGTH = 200


def nonce_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def issue_nonce(
    session: AsyncSession, *, purpose: str, user_id: Any = None, ip_hash: str | None = None
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    await session.execute(delete(AuthNonce).where(AuthNonce.expiresAt < now - timedelta(hours=1)))
    raw = secrets.token_urlsafe(32)
    expires = now + timedelta(minutes=NONCE_MINUTES)
    session.add(
        AuthNonce(
            purpose=purpose, nonceHash=nonce_hash(raw), userId=user_id, ipHash=ip_hash, expiresAt=expires
        )
    )
    await session.commit()
    return raw, expires


async def consume_nonce(session: AsyncSession, raw: str, *, purpose: str, user_id: Any = None) -> bool:
    if not raw or len(raw) > NONCE_MAX_LENGTH:
        return False
    conditions = [
        AuthNonce.nonceHash == nonce_hash(raw),
        AuthNonce.purpose == purpose,
        AuthNonce.usedAt.is_(None),
        AuthNonce.expiresAt > datetime.now(UTC),
    ]
    if user_id is not None:
        conditions.append(AuthNonce.userId == user_id)
    result = await session.execute(update(AuthNonce).where(*conditions).values(usedAt=datetime.now(UTC)))
    return result.rowcount == 1
