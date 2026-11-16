from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

__all__ = ["BINARY_SUFFIXES", "UTF8_BOM", "EncodingViolation", "encoding_violations", "is_binary_path"]

UTF8_BOM = b"\xef\xbb\xbf"

BINARY_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".avif",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".pdf",
        ".parquet",
        ".zip",
        ".gz",
        ".tif",
        ".tiff",
        ".mp3",
        ".mp4",
        ".wav",
        ".webm",
    }
)


@dataclass(frozen=True, order=True)
class EncodingViolation:
    path: str
    reason: str

    def describe(self) -> str:
        return f"{self.path}: {self.reason}"


def is_binary_path(path: PurePosixPath) -> bool:
    return path.suffix.lower() in BINARY_SUFFIXES


def encoding_violations(files: Iterable[tuple[PurePosixPath, bytes]]) -> list[EncodingViolation]:
    found: list[EncodingViolation] = []
    for path, content in files:
        if is_binary_path(path):
            continue
        found.extend(EncodingViolation(str(path), reason) for reason in _problems(content))
    return sorted(found)


def _problems(content: bytes) -> list[str]:
    problems = []
    if content.startswith(UTF8_BOM):
        problems.append("starts with a UTF-8 byte-order mark")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as error:
        problems.append(f"is not valid UTF-8 at byte {error.start}")
    if b"\r" in content:
        problems.append("has a carriage return; line endings must be LF")
    if b"\x00" in content:
        problems.append("has a NUL byte; add its suffix to BINARY_SUFFIXES if it is binary")
    return problems
