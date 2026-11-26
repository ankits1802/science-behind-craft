from __future__ import annotations

import base64
import hashlib
from collections.abc import Sequence
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, ValidationError

from app.core.errors import ExternalFailure

from .base import ContractModel
from .design_critique import NOTE_CHARS, NOTES_MAX, VERDICT_CHARS, DesignNote
from .page_render import CHECKED, DrawingReport, RenderedImage
from .page_report_rules import OPENING
from .structured import StructuredReply, reply_object

__all__ = [
    "DESIGN_READ_CAP_USD",
    "DESIGN_READ_STATES",
    "DESIGN_READ_VERSION",
    "READ",
    "SKIPPED",
    "DesignRead",
    "ModelReading",
    "NotRead",
    "design_read_of",
    "drawing_skip",
    "picture_chapter",
    "pictures_key",
    "skipped",
]

DESIGN_READ_VERSION = 1
DESIGN_READ_CAP_USD = Decimal("0.50")
CUT = "…"
READ, SKIPPED = DESIGN_READ_STATES = ("READ", "SKIPPED")
FIRST_SCREEN_PREFIX = "first-screen-"
CHAPTER_PREFIX = "chapter-"
NO_REPORT = "The preview has no report, so its pictures were not read."
NOT_DRAWN = "The pictures could not be made, so there was nothing to read."
DRAWING_FAILED = (
    "The page failed its drawing checks (rule 28), so the pictures were not read: fix what fails and preview "
    "again, and the read comes with the next drawing."
)
NO_PICTURES = "No picture came back from the drawing, so there was nothing to read."
UNREADABLE = "The server's read answered in a shape that could not be read, so it gives no notes this time."


class DesignRead(ContractModel):
    state: Literal[*DESIGN_READ_STATES]
    verdict: str | None = None
    notes: list[DesignNote] = Field(default_factory=list, max_length=NOTES_MAX)
    chapters: list[str] = Field(default_factory=list)
    reason: str | None = None
    provider: str | None = None
    model: str | None = None
    cost_usd: Decimal = Field(default=Decimal(0), ge=0)
    cap_usd: Decimal = DESIGN_READ_CAP_USD
    cached: bool = False


class ModelReading(ContractModel):
    text: str
    provider: str
    model: str
    cost_usd: Decimal = Field(ge=0)


class NotRead(ContractModel):
    reason: str


def skipped(reason: str) -> DesignRead:
    return DesignRead(state=SKIPPED, reason=reason)


def drawing_skip(drawing: DrawingReport | None, images: Sequence[RenderedImage]) -> str | None:
    if drawing is None:
        return NO_REPORT
    if drawing.state != CHECKED:
        return DRAWING_FAILED if drawing.problems else NOT_DRAWN
    return None if images else NO_PICTURES


def picture_chapter(name: str) -> str:
    if name.startswith(FIRST_SCREEN_PREFIX):
        return OPENING
    return name.removeprefix(CHAPTER_PREFIX)


def pictures_key(images: Sequence[RenderedImage]) -> str:
    digest = hashlib.sha256(f"design-read/{DESIGN_READ_VERSION}".encode())
    for image in images:
        data = base64.b64decode(image.data, validate=True)
        digest.update(f"\n{image.name}\n{len(data)}\n".encode())
        digest.update(data)
    return digest.hexdigest()


def design_read_of(reading: ModelReading, chapters: Sequence[str]) -> DesignRead:
    try:
        answer = reply_object(StructuredReply(text=reading.text, degraded=False))
        notes = [_note(item) for item in _items(answer.get("notes"))]
        verdict = _cut(str(answer.get("verdict") or ""), VERDICT_CHARS)
    except ExternalFailure, ValidationError, TypeError:
        return _unreadable(reading, chapters)
    known = set(chapters)
    return DesignRead(
        state=READ,
        verdict=verdict or None,
        notes=[note for note in notes if note.chapter in known][:NOTES_MAX],
        chapters=list(chapters),
        provider=reading.provider,
        model=reading.model,
        cost_usd=reading.cost_usd,
    )


def _unreadable(reading: ModelReading, chapters: Sequence[str]) -> DesignRead:
    return DesignRead(
        state=SKIPPED,
        reason=UNREADABLE,
        chapters=list(chapters),
        provider=reading.provider,
        model=reading.model,
        cost_usd=reading.cost_usd,
    )


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TypeError("the notes are not a list of objects")
    return value


def _note(item: dict[str, Any]) -> DesignNote:
    return DesignNote(
        chapter=str(item.get("chapter") or ""),
        where=_cut(str(item.get("where") or ""), NOTE_CHARS),
        problem=_cut(str(item.get("problem") or ""), NOTE_CHARS),
        fix=_cut(str(item.get("fix") or ""), NOTE_CHARS),
    )


def _cut(text: str, most: int) -> str:
    words = " ".join(text.split())
    return words if len(words) <= most else words[:most].rstrip() + CUT
