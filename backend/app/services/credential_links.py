import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import PasswordResetToken, User

RESET_MINUTES = 30
INVITE_MINUTES = 60 * 24 * 3
MAX_LINKS_PER_HOUR = 5

MISSING = "MISSING"
MALFORMED = "MALFORMED"
EXPIRED = "EXPIRED"
REVOKED = "REVOKED"
SPENT = "SPENT"
UNKNOWN_ACCOUNT = "UNKNOWN_ACCOUNT"

TOKEN_PREFIX = "kv1_"


class IssueThrottled(Exception):
    pass


@dataclass(frozen=True)
class IssuedLink:
    id: str
    link: str
    expiresAt: str
    purpose: str


@dataclass(frozen=True)
class TokenVerdict:
    ok: bool
    reason: str | None = None
    purpose: str | None = None
    user_id: uuid.UUID | None = None
    issued_by_id: uuid.UUID | None = None
    token_id: uuid.UUID | None = None


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def purpose_for(user: User) -> str:
    return "INVITE" if user.passwordHash is None and user.passwordSetAt is None else "RESET"


def minutes_for(purpose: str) -> int:
    return INVITE_MINUTES if purpose == "INVITE" else RESET_MINUTES


def link_for(raw: str) -> str:
    base = get_settings().public_web_url.rstrip("/")
    return f"{base}/set-password?token={quote(raw, safe='')}"


async def issue_link(
    session: AsyncSession, *, user: User, purpose: str, issued_by_id: uuid.UUID | None
) -> tuple[IssuedLink, str]:
    since = datetime.now(UTC) - timedelta(hours=1)
    recent = (
        await session.execute(
            select(func.count())
            .select_from(PasswordResetToken)
            .where(PasswordResetToken.userId == user.id, PasswordResetToken.createdAt >= since)
        )
    ).scalar_one()
    if recent >= MAX_LINKS_PER_HOUR:
        raise IssueThrottled()
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(minutes=minutes_for(purpose))
    row = PasswordResetToken(
        userId=user.id, tokenHash=token_hash(raw), purpose=purpose, expiresAt=expires, issuedById=issued_by_id
    )
    session.add(row)
    await session.flush()
    return IssuedLink(id=str(row.id), link=link_for(raw), expiresAt=expires.isoformat(), purpose=purpose), raw


async def describe_token(session: AsyncSession, raw: str | None) -> TokenVerdict:
    if not raw:
        return TokenVerdict(False, MISSING)
    if not raw.startswith(TOKEN_PREFIX) or len(raw) > 200:
        return TokenVerdict(False, MALFORMED)
    row = (
        await session.execute(
            select(PasswordResetToken).where(PasswordResetToken.tokenHash == token_hash(raw))
        )
    ).scalar_one_or_none()
    if row is None:
        return TokenVerdict(False, MALFORMED)
    if row.revokedAt is not None:
        return TokenVerdict(False, REVOKED, row.purpose)
    if row.usedAt is not None:
        return TokenVerdict(False, SPENT, row.purpose)
    if row.expiresAt <= datetime.now(UTC):
        return TokenVerdict(False, EXPIRED, row.purpose)
    user = await session.get(User, row.userId)
    if user is None or user.deletedAt is not None:
        return TokenVerdict(False, UNKNOWN_ACCOUNT, row.purpose)
    return TokenVerdict(True, None, row.purpose, row.userId, row.issuedById, row.id)


async def mark_used_and_revoke_rest(session: AsyncSession, verdict: TokenVerdict) -> None:
    now = datetime.now(UTC)
    await session.execute(
        update(PasswordResetToken).where(PasswordResetToken.id == verdict.token_id).values(usedAt=now)
    )
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.userId == verdict.user_id,
            PasswordResetToken.id != verdict.token_id,
            PasswordResetToken.usedAt.is_(None),
            PasswordResetToken.revokedAt.is_(None),
        )
        .values(revokedAt=now)
    )


async def revoke_link(session: AsyncSession, link_id: uuid.UUID) -> bool:
    result = await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.id == link_id,
            PasswordResetToken.revokedAt.is_(None),
            PasswordResetToken.usedAt.is_(None),
        )
        .values(revokedAt=datetime.now(UTC))
    )
    return bool(result.rowcount)


async def revoke_outstanding(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.userId == user_id,
            PasswordResetToken.usedAt.is_(None),
            PasswordResetToken.revokedAt.is_(None),
        )
        .values(revokedAt=datetime.now(UTC))
    )
    return int(result.rowcount or 0)
