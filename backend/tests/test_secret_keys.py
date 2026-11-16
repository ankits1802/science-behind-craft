import logging

import pytest

from app.core.errors import NotConfigured
from app.core.security import secret_key, secret_key_or_none
from app.media.bundle import bundle_key
from app.voice.binding import hmac_key

KEY = "k" * 32


def test_a_key_of_32_characters_is_its_utf8_bytes() -> None:
    assert secret_key("SOME_KEY", KEY) == b"k" * 32


def test_surrounding_whitespace_is_not_part_of_the_key() -> None:
    assert secret_key("SOME_KEY", f"  {KEY}\n") == b"k" * 32
    with pytest.raises(NotConfigured):
        secret_key("SOME_KEY", f"  {'k' * 31}  ")


def test_a_missing_or_short_key_names_itself() -> None:
    for value in (None, "", "short"):
        with pytest.raises(NotConfigured) as refused:
            secret_key("SOME_KEY", value)
        assert refused.value.name == "SOME_KEY"
        assert "32 characters" in refused.value.message


def test_the_media_bundle_and_voice_binding_keys_follow_one_rule() -> None:
    padded = f" {KEY} "
    assert bundle_key(padded) == hmac_key(padded) == secret_key("ANY", padded)
    for read in (bundle_key, hmac_key):
        with pytest.raises(NotConfigured):
            read("k" * 31)


def test_an_unset_key_is_quietly_absent(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        assert secret_key_or_none("SOME_KEY", None) is None
        assert secret_key_or_none("SOME_KEY", "   ") is None
    assert caplog.records == []


def test_a_key_set_too_short_is_absent_and_logged_by_name(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        assert secret_key_or_none("MEDIA_BUNDLE_HMAC_KEY", "too-short-value") is None
    [record] = caplog.records
    assert record.levelno == logging.ERROR
    assert "MEDIA_BUNDLE_HMAC_KEY" in record.getMessage()
    assert "too-short-value" not in record.getMessage()
