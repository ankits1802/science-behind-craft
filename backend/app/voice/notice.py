from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

__all__ = [
    "VOICE_NOTICE_PUBLISHED_AT",
    "VOICE_NOTICE_TITLE",
    "VOICE_NOTICE_VERSION",
    "voice_notice",
    "voice_notice_sha256",
]

NOTICE_PATH = Path(__file__).resolve().parents[1] / "data" / "voice_notice.md"
VOICE_NOTICE_VERSION = "2026-11-16"
VOICE_NOTICE_PUBLISHED_AT = "2026-11-16T00:00:00+05:30"
VOICE_NOTICE_TITLE = "Voice notice"


@lru_cache
def _notice_text() -> str:
    return NOTICE_PATH.read_text(encoding="utf-8")


def voice_notice_sha256() -> str:
    return hashlib.sha256(_notice_text().encode("utf-8")).hexdigest()


def voice_notice(contact_address: str | None) -> dict[str, Any]:
    address = (contact_address or "").strip()
    contact = f", or write to {address}" if address else ""
    return {
        "version": VOICE_NOTICE_VERSION,
        "title": VOICE_NOTICE_TITLE,
        "body": _notice_text().replace("{contact}", contact),
        "publishedAt": VOICE_NOTICE_PUBLISHED_AT,
    }
