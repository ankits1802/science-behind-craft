import base64
import hashlib
import hmac
from dataclasses import replace

import pytest

from app.core.errors import NotConfigured
from app.voice.binding import (
    bearer_matches,
    binding_nonce,
    hmac_key,
    nonce_hash,
    session_is_bound,
    session_nonce,
)

from .fakes import BEARER, CONVERSATION_ID, HMAC_KEY, SESSION_ID, USER_ID, agent_session


def test_the_nonce_is_the_contract_hmac_over_the_binding_fields() -> None:
    message = "\x1f".join(
        ("kalavigyan-voice/v1", str(USER_ID), str(SESSION_ID), CONVERSATION_ID, "1794826000")
    )
    mac = base64.urlsafe_b64encode(hmac.new(HMAC_KEY, message.encode(), hashlib.sha256).digest()).rstrip(b"=")
    expected = f"kvs1.{SESSION_ID}.1794826000.{mac.decode()}"
    nonce = binding_nonce(
        HMAC_KEY, user_id=USER_ID, session_id=SESSION_ID, conversation_id=CONVERSATION_ID, exp=1794826000
    )
    assert nonce == expected
    assert nonce_hash(nonce) == hashlib.sha256(expected.encode()).hexdigest()


def test_the_nonce_expires_when_the_session_can_last_run() -> None:
    record = agent_session()
    assert record.nonce_exp == int(record.expires_at.timestamp()) + record.max_duration_seconds
    assert f".{record.nonce_exp}." in session_nonce(HMAC_KEY, record, CONVERSATION_ID)


def test_a_bound_session_matches_its_own_conversation_only() -> None:
    record = agent_session()
    assert session_is_bound(HMAC_KEY, record, CONVERSATION_ID)
    assert not session_is_bound(HMAC_KEY, record, "conv_forged")


def test_an_altered_row_or_forged_nonce_does_not_bind() -> None:
    record = agent_session()
    assert not session_is_bound(HMAC_KEY, replace(record, nonce_hash="0" * 64), CONVERSATION_ID)
    other_user = replace(record, user_id=SESSION_ID)
    assert not session_is_bound(HMAC_KEY, other_user, CONVERSATION_ID)
    assert not session_is_bound(b"another-binding-key-of-enough-length-000", record, CONVERSATION_ID)


def test_a_nonce_reused_for_another_conversation_does_not_bind() -> None:
    first = agent_session()
    second = replace(first, conversation_id="conv_second", nonce_hash=first.nonce_hash)
    assert not session_is_bound(HMAC_KEY, second, "conv_second")


def test_an_ended_session_has_no_nonce_and_does_not_bind() -> None:
    assert not session_is_bound(HMAC_KEY, replace(agent_session(), nonce_hash=None), CONVERSATION_ID)


def test_the_bearer_must_match_exactly() -> None:
    assert bearer_matches(f"Bearer {BEARER}", BEARER)
    assert not bearer_matches(BEARER, BEARER)
    assert not bearer_matches(f"Bearer {BEARER}x", BEARER)
    assert not bearer_matches(None, BEARER)
    assert not bearer_matches(f"Bearer {BEARER}", None)


def test_a_short_binding_key_is_refused() -> None:
    with pytest.raises(NotConfigured, match="VOICE_SESSION_HMAC_KEY"):
        hmac_key("short")
    assert hmac_key("k" * 32) == b"k" * 32
