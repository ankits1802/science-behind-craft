import asyncio
import base64
import hashlib
import hmac
import logging
import re
import secrets
import struct
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any
from urllib.parse import quote, urlencode

import jwt
import segno
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models import TwoFactorChallenge, User

logger = logging.getLogger(__name__)

DIGITS = 6
PERIOD_SECONDS = 30
WINDOW_STEPS = 1
SECRET_BYTES = 20
TOTP_ISSUER = "KalaVigyan"

RECOVERY_CODE_COUNT = 10
RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
RECOVERY_GROUP = 4

CHALLENGE_PURPOSE = "2fa"
CHALLENGE_MINUTES = 5
MAX_CHALLENGE_ATTEMPTS = 5

FAILURE_BUDGET = 10
RECOVERY_FAILURE_BUDGET = 5
FAILURE_WINDOW = timedelta(minutes=15)
FIRST_LOCKOUT = timedelta(minutes=15)
MAX_LOCKOUT = timedelta(hours=1)
LOCKOUT_DECAY = timedelta(hours=24)
PENDING_SETUP_MINUTES = 15

_CHALLENGE_CONTEXT = b"kalavigyan-two-factor-challenge-v1"
_KEY_ID_CONTEXT = b"kalavigyan-totp-key-id-v2"
_LEGACY_CONTEXT = b"kalavigyan-totp-v1"

LEGACY_PREFIX = "v1"
VERSIONED_PREFIX = "v2:"
KEY_BYTES = 32

WRONG_CODE_DETAIL = "That code didn't work. Check your authenticator app and try again."
CHALLENGE_DEAD_DETAIL = "This sign-in has timed out. Sign in again."
ALREADY_ON_DETAIL = "Two-step verification is already on for this account."
NOT_ON_DETAIL = "Two-step verification is not on for this account."
NO_SETUP_DETAIL = "Start the setup again to get a new key."
TOO_MANY_ATTEMPTS_DETAIL = "Too many attempts. Try again later."
REQUIRED_FOR_ROLE_DETAIL = "Two-step verification is required for your role and cannot be turned off."

TOTP = "totp"
RECOVERY = "recovery"


class TwoFactorError(Exception):
    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


class SecondFactorLocked(Exception):
    pass


class KeyConfigurationError(ValueError):
    pass


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(SECRET_BYTES)).decode("ascii").rstrip("=")


def _b32decode(secret: str) -> bytes:
    cleaned = re.sub(r"\s", "", secret).upper().rstrip("=")
    return base64.b32decode(cleaned + "=" * (-len(cleaned) % 8))


def hotp(key: bytes, counter: int) -> str:
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % 10**DIGITS).zfill(DIGITS)


def time_step(at: float | None = None) -> int:
    return int((time.time() if at is None else at) // PERIOD_SECONDS)


def current_totp(secret: str, at: float | None = None) -> str:
    return hotp(_b32decode(secret), time_step(at))


def match_totp_step(secret: str, code: str, at: float | None = None) -> int | None:
    normalised = re.sub(r"\s", "", code or "")
    if not re.fullmatch(r"[0-9]{6}", normalised):
        return None
    try:
        key = _b32decode(secret)
    except ValueError, TypeError:
        return None
    counter = time_step(at)
    matched: int | None = None
    for offset in range(-WINDOW_STEPS, WINDOW_STEPS + 1):
        if hmac.compare_digest(hotp(key, counter + offset), normalised):
            matched = counter + offset
    return matched


def totp_uri(secret: str, account_name: str, issuer: str = TOTP_ISSUER) -> str:
    label = quote(f"{issuer}:{account_name}", safe="")
    params = urlencode(
        {"secret": secret, "issuer": issuer, "algorithm": "SHA1", "digits": DIGITS, "period": PERIOD_SECONDS},
        quote_via=quote,
    )
    return f"otpauth://totp/{label}?{params}"


def qr_svg(text: str) -> str:
    code = segno.make(text, error="m", micro=False, boost_error=False)
    border = 4
    rows = [[bool(cell) for cell in row] for row in code.matrix]
    size = len(rows[0]) + 2 * border
    commands: list[str] = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if not row[x]:
                x += 1
                continue
            start = x
            while x < len(row) and row[x]:
                x += 1
            commands.append(f"M{start + border} {y + border}h{x - start}v1h-{x - start}z")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" shape-rendering="crispEdges">'
        f'<rect width="{size}" height="{size}" fill="#ffffff"/>'
        f'<path fill="#000000" d="{"".join(commands)}"/></svg>'
    )


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def parse_key(text: str, *, name: str = "TWO_FACTOR_ENCRYPTION_KEY") -> bytes:
    cleaned = re.sub(r"\s", "", text or "")
    try:
        raw = base64.b64decode(
            cleaned.replace("-", "+").replace("_", "/") + "=" * (-len(cleaned) % 4), validate=True
        )
    except ValueError as exc:
        raise KeyConfigurationError(f"{name} is not base64") from exc
    if len(raw) != KEY_BYTES:
        raise KeyConfigurationError(f"{name} must be {KEY_BYTES} random bytes, base64-encoded")
    return raw


def key_id(key: bytes) -> str:
    return _b64(hmac.new(key, _KEY_ID_CONTEXT, hashlib.sha256).digest()[:6])


@dataclass(frozen=True)
class Keyring:
    current: tuple[str, bytes] | None
    readable: dict[str, bytes]


@lru_cache(maxsize=8)
def _keyring(current: str | None, previous: str | None) -> Keyring:
    readable: dict[str, bytes] = {}
    head: tuple[str, bytes] | None = None
    if current and current.strip():
        key = parse_key(current)
        head = (key_id(key), key)
        readable[head[0]] = key
    for index, text in enumerate(part for part in (previous or "").split(",") if part.strip()):
        key = parse_key(text, name=f"TWO_FACTOR_PREVIOUS_KEYS[{index}]")
        readable.setdefault(key_id(key), key)
    return Keyring(current=head, readable=readable)


def keyring() -> Keyring:
    settings = get_settings()
    return _keyring(settings.two_factor_encryption_key, settings.two_factor_previous_keys)


@lru_cache(maxsize=4)
def _legacy_key(jwt_secret: str) -> bytes:
    return hashlib.scrypt(jwt_secret.encode("utf-8"), salt=_LEGACY_CONTEXT, n=2**14, r=8, p=1, dklen=32)


def _seal(key: bytes, plain: str, aad: bytes | None) -> tuple[str, str, str]:
    iv = secrets.token_bytes(12)
    sealed = AESGCM(key).encrypt(iv, plain.encode("utf-8"), aad)
    return _b64(iv), _b64(sealed[-16:]), _b64(sealed[:-16])


def encrypt_secret(plain: str) -> str:
    ring = keyring()
    if ring.current is None:
        return ".".join((LEGACY_PREFIX, *_seal(_legacy_key(get_settings().jwt_secret), plain, None)))
    kid, key = ring.current
    label = f"{VERSIONED_PREFIX}{kid}"
    return ".".join((label, *_seal(key, plain, label.encode("ascii"))))


def decrypt_secret(stored: str | None) -> str | None:
    if not stored:
        return None
    parts = stored.split(".")
    if len(parts) != 4:
        return None
    label = parts[0]
    aad: bytes | None
    if label == LEGACY_PREFIX:
        key, aad = _legacy_key(get_settings().jwt_secret), None
    elif label.startswith(VERSIONED_PREFIX):
        found = keyring().readable.get(label[len(VERSIONED_PREFIX) :])
        if found is None:
            return None
        key, aad = found, label.encode("ascii")
    else:
        return None
    try:
        iv, tag, ciphertext = _unb64(parts[1]), _unb64(parts[2]), _unb64(parts[3])
        return AESGCM(key).decrypt(iv, ciphertext + tag, aad).decode("utf-8")
    except InvalidTag, ValueError:
        return None


def verify_key_configuration() -> None:
    settings = get_settings()
    try:
        keyring()
    except KeyConfigurationError as exc:
        raise RuntimeError(str(exc)) from exc
    if settings.is_production and not (settings.two_factor_encryption_key or "").strip():
        raise RuntimeError("TWO_FACTOR_ENCRYPTION_KEY must be set in production")


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(RECOVERY_GROUP * 2))
        codes.append(f"{raw[:RECOVERY_GROUP]}-{raw[RECOVERY_GROUP:]}")
    return codes


def canonical_recovery_code(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]", "", (text or "").lower())
    if len(cleaned) == RECOVERY_GROUP * 2:
        return f"{cleaned[:RECOVERY_GROUP]}-{cleaned[RECOVERY_GROUP:]}"
    return cleaned


def code_kind(text: str) -> str | None:
    compact = re.sub(r"[\s-]", "", text or "")
    if re.fullmatch(r"[0-9]{6}", compact):
        return TOTP
    if re.fullmatch(r"[A-Za-z0-9]{8}", compact):
        return RECOVERY
    return None


async def hash_recovery_codes(codes: list[str]) -> list[str]:
    return list(
        await asyncio.gather(*(asyncio.to_thread(hash_password, canonical_recovery_code(c)) for c in codes))
    )


async def _matching_hash(stored: list[str], submitted: str) -> str | None:
    canonical = canonical_recovery_code(submitted)
    verdicts = await asyncio.gather(*(asyncio.to_thread(verify_password, canonical, h) for h in stored))
    match = None
    for hashed, ok in zip(stored, verdicts, strict=True):
        if ok:
            match = hashed
    return match


@dataclass(frozen=True)
class AttemptBudget:
    name: str
    limit: int
    attempts: str
    window_started: str
    locked_until: str
    lockouts: str


CODE_BUDGET = AttemptBudget(
    "code",
    FAILURE_BUDGET,
    "twoFactorFailedAttempts",
    "twoFactorFailureWindowStartedAt",
    "twoFactorLockedUntil",
    "twoFactorLockouts",
)
RECOVERY_BUDGET = AttemptBudget(
    "recovery",
    RECOVERY_FAILURE_BUDGET,
    "twoFactorRecoveryFailedAttempts",
    "twoFactorRecoveryWindowStartedAt",
    "twoFactorRecoveryLockedUntil",
    "twoFactorRecoveryLockouts",
)
BUDGETS = (CODE_BUDGET, RECOVERY_BUDGET)

CLEAR_FAILURES: dict[str, Any] = {
    column: value
    for budget in BUDGETS
    for column, value in (
        (budget.attempts, 0),
        (budget.window_started, None),
        (budget.locked_until, None),
        (budget.lockouts, 0),
    )
}


def lockout_duration(previous_lockouts: int) -> timedelta:
    return min(FIRST_LOCKOUT * (2 ** min(max(previous_lockouts, 0), 16)), MAX_LOCKOUT)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def is_locked(user: Any, budget: AttemptBudget = CODE_BUDGET, now: datetime | None = None) -> bool:
    until = _aware(getattr(user, budget.locked_until, None))
    return until is not None and until > (now or datetime.now(UTC))


def fully_locked(user: Any, now: datetime | None = None) -> bool:
    return all(is_locked(user, budget, now) for budget in BUDGETS)


def budget_for(code: str, *, allow_recovery: bool = True) -> AttemptBudget:
    return RECOVERY_BUDGET if allow_recovery and code_kind(code) == RECOVERY else CODE_BUDGET


def _col(name: str) -> Any:
    return getattr(User, name)


async def _fresh(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return (
        await session.execute(
            select(User).where(User.id == user_id).execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()


async def consume_totp_step(session: AsyncSession, user_id: uuid.UUID, step: int) -> bool:
    result = await session.execute(
        update(User)
        .where(User.id == user_id, or_(User.twoFactorLastStep.is_(None), User.twoFactorLastStep < step))
        .values(twoFactorLastStep=step)
    )
    return result.rowcount == 1


async def consume_recovery_code(session: AsyncSession, user: User, submitted: str) -> bool:
    stored = list(user.twoFactorRecoveryCodes or [])
    if not stored:
        return False
    match = await _matching_hash(stored, submitted)
    if match is None:
        return False
    remaining = [hashed for hashed in stored if hashed != match]
    result = await session.execute(
        update(User)
        .where(User.id == user.id, User.twoFactorRecoveryCodes == stored)
        .values(twoFactorRecoveryCodes=remaining)
    )
    return result.rowcount == 1


async def verify_second_factor(
    session: AsyncSession, user: User, code: str, *, allow_recovery: bool = True
) -> str | None:
    kind = code_kind(code)
    if kind == TOTP:
        secret = decrypt_secret(user.twoFactorSecret)
        if secret is None:
            return None
        step = match_totp_step(secret, code)
        if step is None or not await consume_totp_step(session, user.id, step):
            return None
        return TOTP
    if kind == RECOVERY and allow_recovery:
        return RECOVERY if await consume_recovery_code(session, user, code) else None
    return None


async def claim_attempt_slot(session: AsyncSession, user_id: uuid.UUID, budget: AttemptBudget) -> int:
    now = datetime.now(UTC)
    row = await _fresh(session, user_id)
    if row is None or is_locked(row, budget, now):
        raise SecondFactorLocked()
    started = _aware(getattr(row, budget.window_started))
    if started is None or now - started > FAILURE_WINDOW:
        values: dict[str, Any] = {budget.attempts: 0, budget.window_started: now}
        last_lock_end = _aware(getattr(row, budget.locked_until))
        if last_lock_end is not None and now - last_lock_end > LOCKOUT_DECAY:
            values[budget.lockouts] = 0
        await session.execute(update(User).where(User.id == user_id).values(**values))
    claimed = await session.execute(
        update(User)
        .where(
            User.id == user_id,
            _col(budget.attempts) < budget.limit,
            or_(_col(budget.locked_until).is_(None), _col(budget.locked_until) < now),
        )
        .values({budget.attempts: _col(budget.attempts) + 1})
        .returning(_col(budget.attempts))
    )
    count = claimed.scalar_one_or_none()
    if count is None:
        raise SecondFactorLocked()
    return int(count)


async def settle_success(session: AsyncSession, user_id: uuid.UUID, budget: AttemptBudget) -> None:
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values({budget.attempts: 0, budget.window_started: None, budget.lockouts: 0})
    )


async def lock_if_spent(session: AsyncSession, user_id: uuid.UUID, budget: AttemptBudget) -> bool:
    row = await _fresh(session, user_id)
    if row is None or (getattr(row, budget.attempts) or 0) < budget.limit:
        return False
    now = datetime.now(UTC)
    lockouts = int(getattr(row, budget.lockouts) or 0)
    until = now + lockout_duration(lockouts)
    result = await session.execute(
        update(User)
        .where(User.id == user_id, _col(budget.attempts) >= budget.limit)
        .values({budget.locked_until: until, budget.window_started: None, budget.lockouts: lockouts + 1})
    )
    if result.rowcount:
        logger.warning("two-factor locked", extra={"userId": str(user_id), "budget": budget.name})
    return bool(result.rowcount)


async def check_second_factor(
    session: AsyncSession, user: User, code: str, *, allow_recovery: bool = True
) -> bool:
    budget = budget_for(code, allow_recovery=allow_recovery)
    await claim_attempt_slot(session, user.id, budget)
    await session.commit()
    fresh = await _fresh(session, user.id)
    if fresh is None:
        return False
    if budget is RECOVERY_BUDGET:
        accepted = await consume_recovery_code(session, fresh, code)
    else:
        accepted = await verify_second_factor(session, fresh, code, allow_recovery=False) is not None
    if accepted:
        await settle_success(session, user.id, budget)
        await session.commit()
        return True
    await lock_if_spent(session, user.id, budget)
    await session.commit()
    return False


def _challenge_key() -> bytes:
    return hmac.new(get_settings().jwt_secret.encode("utf-8"), _CHALLENGE_CONTEXT, hashlib.sha256).digest()


@dataclass(frozen=True)
class Challenge:
    user_id: uuid.UUID
    challenge_id: uuid.UUID


async def issue_challenge(session: AsyncSession, user: User) -> str:
    now = datetime.now(UTC)
    await session.execute(delete(TwoFactorChallenge).where(TwoFactorChallenge.expiresAt < now))
    expires = now + timedelta(minutes=CHALLENGE_MINUTES)
    row = TwoFactorChallenge(userId=user.id, expiresAt=expires)
    session.add(row)
    await session.flush()
    await session.commit()
    return jwt.encode(
        {
            "sub": str(user.id),
            "jti": str(row.id),
            "purpose": CHALLENGE_PURPOSE,
            "iat": int(now.timestamp()),
            "exp": expires,
        },
        _challenge_key(),
        algorithm="HS256",
    )


def read_challenge(token: str) -> Challenge:
    try:
        claims = jwt.decode(
            token or "", _challenge_key(), algorithms=["HS256"], options={"require": ["exp", "sub", "jti"]}
        )
        if claims.get("purpose") != CHALLENGE_PURPOSE:
            raise TwoFactorError("dead", CHALLENGE_DEAD_DETAIL)
        return Challenge(user_id=uuid.UUID(str(claims["sub"])), challenge_id=uuid.UUID(str(claims["jti"])))
    except (jwt.PyJWTError, ValueError) as exc:
        raise TwoFactorError("dead", CHALLENGE_DEAD_DETAIL) from exc


async def spend_challenge_attempt(session: AsyncSession, challenge: Challenge) -> bool:
    result = await session.execute(
        update(TwoFactorChallenge)
        .where(
            TwoFactorChallenge.id == challenge.challenge_id,
            TwoFactorChallenge.userId == challenge.user_id,
            TwoFactorChallenge.usedAt.is_(None),
            TwoFactorChallenge.attempts < MAX_CHALLENGE_ATTEMPTS,
            TwoFactorChallenge.expiresAt > datetime.now(UTC),
        )
        .values(attempts=TwoFactorChallenge.attempts + 1)
    )
    await session.commit()
    return result.rowcount == 1


async def close_challenge(session: AsyncSession, challenge: Challenge) -> bool:
    result = await session.execute(
        update(TwoFactorChallenge)
        .where(TwoFactorChallenge.id == challenge.challenge_id, TwoFactorChallenge.usedAt.is_(None))
        .values(usedAt=datetime.now(UTC))
    )
    return result.rowcount == 1


def pending_is_live(user: Any, now: datetime | None = None) -> bool:
    if getattr(user, "twoFactorEnabled", False) or not getattr(user, "twoFactorPendingSecret", None):
        return False
    since = _aware(getattr(user, "twoFactorPendingSince", None))
    if since is None:
        return False
    return (now or datetime.now(UTC)) - since < timedelta(minutes=PENDING_SETUP_MINUTES)


def status_of(user: Any, now: datetime | None = None) -> dict[str, Any]:
    from app.core.roles import requires_two_factor

    enabled = bool(getattr(user, "twoFactorEnabled", False))
    enabled_at = getattr(user, "twoFactorEnabledAt", None) if enabled else None
    return {
        "enabled": enabled,
        "pending": pending_is_live(user, now),
        "required": requires_two_factor(user),
        "recovery_codes_remaining": len(getattr(user, "twoFactorRecoveryCodes", None) or [])
        if enabled
        else 0,
        "enabled_at": enabled_at.isoformat() if enabled_at else None,
    }


async def clear_pending(session: AsyncSession, user_id: uuid.UUID) -> bool:
    result = await session.execute(
        update(User)
        .where(User.id == user_id, User.twoFactorEnabled.is_(False), User.twoFactorPendingSecret.is_not(None))
        .values(twoFactorPendingSecret=None, twoFactorPendingSince=None)
    )
    return bool(result.rowcount)


async def begin_setup(session: AsyncSession, user: User) -> dict[str, str]:
    if user.twoFactorEnabled:
        raise TwoFactorError("conflict", ALREADY_ON_DETAIL)
    secret = generate_secret()
    user.twoFactorPendingSecret = encrypt_secret(secret)
    user.twoFactorPendingSince = datetime.now(UTC)
    await session.commit()
    uri = totp_uri(secret, user.email)
    return {"secret": secret, "otpauth_uri": uri, "qr_svg": qr_svg(uri)}


async def enable(session: AsyncSession, user: User, code: str) -> list[str]:
    if user.twoFactorEnabled:
        raise TwoFactorError("conflict", ALREADY_ON_DETAIL)
    pending = user.twoFactorPendingSecret
    secret = decrypt_secret(pending) if pending_is_live(user) else None
    if secret is None:
        raise TwoFactorError("invalid", NO_SETUP_DETAIL)
    step = match_totp_step(secret, code)
    if step is None:
        raise TwoFactorError("invalid", WRONG_CODE_DETAIL)
    codes = generate_recovery_codes()
    hashes = await hash_recovery_codes(codes)
    result = await session.execute(
        update(User)
        .where(User.id == user.id, User.twoFactorEnabled.is_(False), User.twoFactorPendingSecret == pending)
        .values(
            twoFactorEnabled=True,
            twoFactorSecret=encrypt_secret(secret),
            twoFactorPendingSecret=None,
            twoFactorPendingSince=None,
            twoFactorRecoveryCodes=hashes,
            twoFactorLastStep=step,
            twoFactorEnabledAt=datetime.now(UTC),
            tokenVersion=User.tokenVersion + 1,
        )
    )
    if result.rowcount != 1:
        raise TwoFactorError("conflict", NO_SETUP_DETAIL)
    await session.commit()
    return codes


OFF_VALUES: dict[str, Any] = {
    "twoFactorEnabled": False,
    "twoFactorSecret": None,
    "twoFactorPendingSecret": None,
    "twoFactorPendingSince": None,
    "twoFactorRecoveryCodes": [],
    "twoFactorLastStep": None,
    "twoFactorEnabledAt": None,
    **CLEAR_FAILURES,
}


async def _checked(session: AsyncSession, user: User, code: str, *, allow_recovery: bool = True) -> bool:
    try:
        return await check_second_factor(session, user, code, allow_recovery=allow_recovery)
    except SecondFactorLocked as exc:
        raise TwoFactorError("locked", TOO_MANY_ATTEMPTS_DETAIL) from exc


async def disable(session: AsyncSession, user: User, code: str) -> str:
    from app.core.roles import requires_two_factor

    if not user.twoFactorEnabled:
        raise TwoFactorError("conflict", NOT_ON_DETAIL)
    if requires_two_factor(user):
        raise TwoFactorError("conflict", REQUIRED_FOR_ROLE_DETAIL)
    if not await _checked(session, user, code):
        raise TwoFactorError("invalid", WRONG_CODE_DETAIL)
    await session.execute(
        update(User).where(User.id == user.id).values(**OFF_VALUES, tokenVersion=User.tokenVersion + 1)
    )
    await session.commit()
    return code_kind(code) or TOTP


async def regenerate_recovery_codes(session: AsyncSession, user: User, code: str) -> list[str]:
    if not user.twoFactorEnabled:
        raise TwoFactorError("conflict", NOT_ON_DETAIL)
    if not await _checked(session, user, code, allow_recovery=False):
        raise TwoFactorError("invalid", WRONG_CODE_DETAIL)
    codes = generate_recovery_codes()
    hashes = await hash_recovery_codes(codes)
    await session.execute(update(User).where(User.id == user.id).values(twoFactorRecoveryCodes=hashes))
    await session.commit()
    return codes


async def reset_by_administrator(session: AsyncSession, target: User) -> int:
    destroyed = len(target.twoFactorRecoveryCodes or [])
    await session.execute(
        update(User)
        .where(User.id == target.id)
        .values(**OFF_VALUES, tokenVersion=User.tokenVersion + 1, sessionsValidFrom=datetime.now(UTC))
    )
    return destroyed


async def step_up(session: AsyncSession, user: User, code: str | None) -> bool:
    if not user.twoFactorEnabled or not code:
        return False
    try:
        return await check_second_factor(session, user, code, allow_recovery=False)
    except SecondFactorLocked:
        return False
