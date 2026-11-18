from __future__ import annotations

import base64
import hashlib
import hmac
import uuid

from app.core.security import secret_key

from .records import SessionRecord

__all__ = [
    "ARTISAN_NONCE_CONTEXT",
    "HMAC_KEY_NAME",
    "NONCE_CONTEXT",
    "NONCE_PREFIX",
    "bearer_matches",
    "binding_nonce",
    "hmac_key",
    "nonce_hash",
    "session_is_bound",
    "session_nonce",
]

NONCE_PREFIX = "kvs1"
NONCE_CONTEXT = "kalavigyan-voice/v1"
ARTISAN_NONCE_CONTEXT = "kalavigyan-artisan/v1"
FIELD_SEPARATOR = "\x1f"
HMAC_KEY_NAME = "VOICE_SESSION_HMAC_KEY"
BEARER_PREFIX = "Bearer "


def hmac_key(value: str | None) -> bytes:
    return secret_key(HMAC_KEY_NAME, value)


def binding_nonce(
    key: bytes,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    conversation_id: str,
    exp: int,
    context: str = NONCE_CONTEXT,
) -> str:
    message = FIELD_SEPARATOR.join((context, str(user_id), str(session_id), conversation_id, str(exp)))
    mac = hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()
    encoded = base64.urlsafe_b64encode(mac).decode("ascii").rstrip("=")
    return f"{NONCE_PREFIX}.{session_id}.{exp}.{encoded}"


def nonce_hash(nonce: str) -> str:
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


def session_nonce(
    key: bytes, record: SessionRecord, conversation_id: str, *, context: str = NONCE_CONTEXT
) -> str:
    return binding_nonce(
        key,
        user_id=record.user_id,
        session_id=record.id,
        conversation_id=conversation_id,
        exp=record.nonce_exp,
        context=context,
    )


def session_is_bound(
    key: bytes, record: SessionRecord, conversation_id: str, *, context: str = NONCE_CONTEXT
) -> bool:
    if not record.nonce_hash or record.conversation_id is None:
        return False
    expected = nonce_hash(session_nonce(key, record, conversation_id, context=context))
    same_hash = hmac.compare_digest(expected, record.nonce_hash)
    same_conversation = hmac.compare_digest(record.conversation_id.encode(), conversation_id.encode())
    return same_hash and same_conversation


def bearer_matches(authorization: str | None, expected: str | None) -> bool:
    secret = (expected or "").strip()
    given = authorization or ""
    if not secret or not given.startswith(BEARER_PREFIX):
        return False
    return hmac.compare_digest(given[len(BEARER_PREFIX) :].strip().encode("utf-8"), secret.encode("utf-8"))
