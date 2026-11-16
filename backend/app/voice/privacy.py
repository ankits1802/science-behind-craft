from __future__ import annotations

import json
import re
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.errors import InvalidInput, NotConfigured
from app.research.evidence import without_personal_data
from app.research.untrusted import clean_untrusted_text

__all__ = ["HEARD_MAX_CHARS", "TranscriptCipher", "heard_text", "transcript_cipher"]

HEARD_MAX_CHARS = 2000
WHITESPACE = re.compile(r"\s+")
TRANSCRIPT_KEY_NAME = "TRANSCRIPT_ENCRYPTION_KEY"


class TranscriptCipher:
    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.strip().encode("ascii"))
        except ValueError, UnicodeEncodeError:
            raise NotConfigured(TRANSCRIPT_KEY_NAME, f"{TRANSCRIPT_KEY_NAME} is not a Fernet key") from None

    def seal(self, transcript: dict[str, Any]) -> str:
        text = json.dumps(transcript, ensure_ascii=False, separators=(",", ":"))
        return self._fernet.encrypt(text.encode("utf-8")).decode("ascii")

    def open(self, sealed: str | None) -> dict[str, Any]:
        if not sealed:
            return {}
        try:
            plain = self._fernet.decrypt(sealed.encode("ascii"))
        except InvalidToken:
            raise InvalidInput("The stored voice transcript does not open with the current key") from None
        opened = json.loads(plain.decode("utf-8"))
        if not isinstance(opened, dict):
            raise InvalidInput("The stored voice transcript is not an object")
        return opened


def transcript_cipher(key: str | None) -> TranscriptCipher:
    if not (key or "").strip():
        raise NotConfigured(TRANSCRIPT_KEY_NAME, f"{TRANSCRIPT_KEY_NAME} is not set")
    return TranscriptCipher(key or "")


def heard_text(text: str) -> str:
    cleaned = WHITESPACE.sub(" ", without_personal_data(clean_untrusted_text(text))).strip()
    return cleaned[:HEARD_MAX_CHARS].strip()
