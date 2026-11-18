from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.research.testimony import RECORDING_NOTICE_VERSION
from app.research.vocabulary import ANSWER_LANGUAGES, CANONICAL_LANGUAGE

__all__ = [
    "RECORDING_NOTICE_PUBLISHED_AT",
    "RECORDING_NOTICE_TITLE",
    "RECORDING_NOTICE_VERSION",
    "notice_language",
    "recording_notice",
    "recording_notice_sha256",
]

DATA = Path(__file__).resolve().parents[1] / "data"
RECORDING_NOTICE_PUBLISHED_AT = "2026-11-18T00:00:00+05:30"
RECORDING_NOTICE_TITLE = "Recording notice"


def _path(language: str) -> Path:
    if language == CANONICAL_LANGUAGE:
        return DATA / "artisan_recording_notice.md"
    return DATA / f"artisan_recording_notice.{language}.md"


def notice_language(language: str | None) -> str:
    if language in ANSWER_LANGUAGES and _path(language).is_file():
        return language
    return CANONICAL_LANGUAGE


@lru_cache
def _text(language: str) -> str:
    return _path(language).read_text(encoding="utf-8")


def recording_notice_sha256() -> str:
    return hashlib.sha256(_text(CANONICAL_LANGUAGE).encode("utf-8")).hexdigest()


def recording_notice(language: str | None, contact_address: str | None) -> dict[str, Any]:
    shown = notice_language(language)
    address = (contact_address or "").strip()
    contact = f", or write to {address}" if address else ""
    return {
        "version": RECORDING_NOTICE_VERSION,
        "language": shown,
        "title": RECORDING_NOTICE_TITLE,
        "body": _text(shown).replace("{contact}", contact),
        "publishedAt": RECORDING_NOTICE_PUBLISHED_AT,
    }
