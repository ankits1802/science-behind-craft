from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.core.errors import ExternalFailure

__all__ = [
    "ELEVENLABS_SERVICE",
    "GENERATION_FAILURE_REASONS",
    "GENERATION_STATUSES",
    "SPEECH_MAX_BYTES",
    "Generation",
    "aligned_times",
    "checked_audio",
    "created_generation",
    "decoded_audio",
    "generation_of",
    "has_text",
    "id_in",
    "named_tool",
    "off_contract",
]

ELEVENLABS_SERVICE = "elevenlabs"
SPEECH_MAX_BYTES = 8 * 1024 * 1024
GENERATION_STATUSES = frozenset({"pending", "generating", "completed", "failed"})
GENERATION_FAILURE_REASONS = frozenset(
    {
        "timeout",
        "model_error",
        "moderated",
        "invalid_parameters",
        "dependency_failed",
        "charging_failed",
        "internal_error",
    }
)


@dataclass(frozen=True)
class Generation:
    generation_id: str
    status: str
    content_url: str | None = None
    mime: str | None = None
    failure_reason: str | None = None
    message: str | None = None

    @property
    def open(self) -> bool:
        return self.status in {"pending", "generating"}


def has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def checked_audio(audio: bytes) -> bytes:
    if not audio or len(audio) > SPEECH_MAX_BYTES:
        raise off_contract(f"audio ({len(audio)} bytes)")
    return audio


def decoded_audio(value: Any) -> bytes:
    if not has_text(value):
        raise off_contract("narration audio")
    try:
        return base64.b64decode(value, validate=True)
    except binascii.Error:
        raise off_contract("narration audio") from None


def aligned_times(text: str, alignment: Any) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not isinstance(alignment, dict):
        raise off_contract("narration alignment")
    marks = alignment.get("characters")
    starts = alignment.get("character_start_times_seconds")
    ends = alignment.get("character_end_times_seconds")
    if not (isinstance(marks, list) and isinstance(starts, list) and isinstance(ends, list)):
        raise off_contract("narration alignment")
    if not len(marks) == len(starts) == len(ends):
        raise off_contract("narration alignment")
    if not all(map(_timed_mark, marks, starts, ends, strict=True)):
        raise off_contract("narration alignment")
    if "".join(marks) != text:
        raise off_contract("narration alignment, which does not spell the text sent,")
    spread = [
        (float(start), float(end)) for mark, start, end in zip(marks, starts, ends, strict=True) for _ in mark
    ]
    return tuple(start for start, _ in spread), tuple(end for _, end in spread)


def created_generation(body: Mapping[str, Any]) -> str:
    if body.get("status") != "pending" or not has_text(body.get("id")):
        raise off_contract("created generation")
    return str(body["id"])


def generation_of(body: Mapping[str, Any], generation_id: str) -> Generation:
    status = body.get("status")
    if body.get("id") != generation_id or status not in GENERATION_STATUSES:
        raise off_contract(f"generation {generation_id}")
    if status == "completed":
        url, mime = body.get("content_url"), body.get("content_mime_type")
        if not has_text(url) or not has_text(mime):
            raise off_contract(f"completed generation {generation_id}")
        return Generation(generation_id, status, content_url=url, mime=mime)
    if status == "failed":
        reason, message = body.get("failure_reason"), body.get("error_message")
        if reason not in GENERATION_FAILURE_REASONS or not isinstance(message, str):
            raise off_contract(f"failed generation {generation_id}")
        return Generation(generation_id, status, failure_reason=reason, message=message)
    return Generation(generation_id, status)


def named_tool(tool: Mapping[str, Any]) -> bool:
    config = tool.get("tool_config")
    return isinstance(config, dict) and has_text(config.get("name")) and has_text(tool.get("id"))


def id_in(body: Mapping[str, Any], field: str, what: str) -> str:
    value = body.get(field)
    if not has_text(value):
        raise off_contract(f"created {what}")
    return str(value)


def off_contract(what: str) -> ExternalFailure:
    return ExternalFailure(
        f"ElevenLabs {what} answer is off its documented shape", service=ELEVENLABS_SERVICE
    )


def _timed_mark(mark: Any, start: Any, end: Any) -> bool:
    numbers = isinstance(start, int | float) and isinstance(end, int | float)
    return isinstance(mark, str) and bool(mark) and numbers and 0 <= start <= end
