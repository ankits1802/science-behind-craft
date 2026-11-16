import base64

import pytest

from app.core.errors import InvalidInput, NotConfigured
from app.voice.privacy import TranscriptCipher, heard_text, transcript_cipher

from .fakes import cipher


@pytest.mark.parametrize(
    ("said", "stored"),
    [
        ("Call me on 98765 43210 about indigo", "Call me on [number] about indigo"),
        ("my mail is asha.k@example.com thanks", "my mail is [email] thanks"),
        ("write to asha at example dot com please", "write to [email] please"),
        ("Aadhaar 1234 5678 9012 is mine", "Aadhaar [number] is mine"),
        ("+91 98765-43210 is my phone", "[number] is my phone"),
    ],
)
def test_phone_numbers_and_email_addresses_are_scrubbed_before_storage(said: str, stored: str) -> None:
    assert heard_text(said) == stored


def test_heard_text_keeps_the_question_and_drops_invisible_characters() -> None:
    assert heard_text("  Why do Ajrakh\u200b printers\n use alum?  ") == "Why do Ajrakh printers use alum?"
    assert len(heard_text("word " * 1000)) <= 2000


def test_the_transcript_is_sealed_and_opened_with_the_key() -> None:
    sealed = cipher().seal({"turns": [{"heard": "Why alum?"}]})
    assert "alum" not in sealed
    assert cipher().open(sealed) == {"turns": [{"heard": "Why alum?"}]}
    assert cipher().open(None) == {}


def test_a_transcript_sealed_with_another_key_does_not_open() -> None:
    other = TranscriptCipher(base64.urlsafe_b64encode(b"x" * 32).decode())
    with pytest.raises(InvalidInput, match="does not open"):
        cipher().open(other.seal({"turns": []}))


def test_a_missing_or_malformed_transcript_key_is_not_configured() -> None:
    with pytest.raises(NotConfigured, match="TRANSCRIPT_ENCRYPTION_KEY"):
        transcript_cipher(None)
    with pytest.raises(NotConfigured, match="Fernet"):
        transcript_cipher("not-a-key")
