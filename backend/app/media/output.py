from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import InvalidInput
from app.providers.base import MediaResult
from app.schemas.media import MEDIA_OUTPUT

from .mp4 import video_facts, without_audio

__all__ = ["PNG_SIGNATURE", "StoredOutput", "checked_output", "png_size"]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IHDR = b"IHDR"


@dataclass(frozen=True)
class StoredOutput:
    data: bytes
    mime: str
    width: int
    height: int
    duration_seconds: float | None


def checked_output(kind: str, result: MediaResult) -> StoredOutput:
    expected = str(MEDIA_OUTPUT[kind]["mime"])
    if result.mime != expected:
        raise InvalidInput(f"A {kind} job stores {expected}, not {result.mime}")
    if kind == "IMAGE":
        width, height = png_size(result.data)
        return StoredOutput(result.data, expected, width, height, None)
    silent = without_audio(result.data)
    facts = video_facts(silent)
    limit = float(MEDIA_OUTPUT["VIDEO"]["seconds"])
    if facts.has_audio or not 0 < facts.duration_seconds <= limit:
        raise InvalidInput(
            f"A stored video is silent and at most {limit:g} s, not {facts.duration_seconds} s"
        )
    return StoredOutput(silent, expected, facts.width, facts.height, facts.duration_seconds)


def png_size(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or not data.startswith(PNG_SIGNATURE) or data[12:16] != IHDR:
        raise InvalidInput("The image is not a PNG")
    width = int.from_bytes(data[16:20])
    height = int.from_bytes(data[20:24])
    if width < 1 or height < 1:
        raise InvalidInput("The PNG has no size")
    return width, height
