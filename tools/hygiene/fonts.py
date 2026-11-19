from __future__ import annotations

import struct
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

__all__ = ["WEB_FONT_ROOT", "FontViolation", "font_tables", "font_violations"]

WEB_FONT_ROOT = PurePosixPath("frontend")

WOFF2_SIGNATURE = b"wOF2"
WOFF2_HEADER_SIZE = 48
SFNT_HEADER_SIZE = 12
SFNT_RECORD_SIZE = 16
SFNT_SUFFIXES = frozenset({".ttf", ".otf"})
WOFF2_ARBITRARY_TAG = 63
WOFF2_NULL_TRANSFORM_OF_GLYF = 3

WOFF2_KNOWN_TAGS = (
    "cmap head hhea hmtx maxp name OS/2 post cvt  fpgm glyf loca prep CFF  VORG EBDT EBLC gasp hdmx kern "
    "LTSH PCLT VDMX vhea vmtx BASE GDEF GPOS GSUB EBSC JSTF MATH CBDT CBLC COLR CPAL SVG  sbix acnt avar bdat "
    "bloc bsln cvar fdsc feat fmtx fvar gvar hsty just lcar mort morx opbd prop trak Zapf Silf Glat Gloc Feat Sill"
)

UNHINTED_REASON = (
    "has TrueType outlines but no prep table, so FreeType (Linux, Android, ChromeOS) auto-hints it and "
    "draws it heavier and snapped; add the fix-unhinted prep (PUSHW 511 SCANCTRL PUSHB 4 SCANTYPE)"
)


@dataclass(frozen=True, order=True)
class FontViolation:
    path: str
    reason: str

    def describe(self) -> str:
        return f"{self.path}: {self.reason}"


def font_violations(files: Iterable[tuple[PurePosixPath, bytes]]) -> list[FontViolation]:
    found = []
    for path, content in files:
        if not path.is_relative_to(WEB_FONT_ROOT):
            continue
        reason = _font_problem(path, content)
        if reason:
            found.append(FontViolation(str(path), reason))
    return sorted(found)


def font_tables(path: PurePosixPath, content: bytes) -> frozenset[str] | None:
    suffix = path.suffix.lower()
    if suffix == ".woff2":
        return _woff2_tables(content)
    if suffix in SFNT_SUFFIXES:
        return _sfnt_tables(content)
    return None


def _font_problem(path: PurePosixPath, content: bytes) -> str | None:
    try:
        tables = font_tables(path, content)
    except (ValueError, IndexError, struct.error) as error:
        return f"cannot be read as a font: {error}"
    if tables is not None and "glyf" in tables and "prep" not in tables:
        return UNHINTED_REASON
    return None


def _sfnt_tables(content: bytes) -> frozenset[str]:
    (count,) = struct.unpack_from(">H", content, 4)
    offsets = range(SFNT_HEADER_SIZE, SFNT_HEADER_SIZE + count * SFNT_RECORD_SIZE, SFNT_RECORD_SIZE)
    return frozenset(content[offset : offset + 4].decode("latin-1").strip() for offset in offsets)


def _woff2_tables(content: bytes) -> frozenset[str]:
    if content[:4] != WOFF2_SIGNATURE:
        raise ValueError("not a WOFF2 file: the signature is not wOF2")
    (count,) = struct.unpack_from(">H", content, 12)
    known = [WOFF2_KNOWN_TAGS[index : index + 4] for index in range(0, len(WOFF2_KNOWN_TAGS), 5)]
    tags = []
    offset = WOFF2_HEADER_SIZE
    for _ in range(count):
        tag, offset = _woff2_entry(content, offset, known)
        tags.append(tag)
    return frozenset(tags)


def _woff2_entry(content: bytes, offset: int, known: list[str]) -> tuple[str, int]:
    flags = content[offset]
    offset += 1
    if flags & 0x3F == WOFF2_ARBITRARY_TAG:
        tag = content[offset : offset + 4].decode("latin-1")
        offset += 4
    else:
        tag = known[flags & 0x3F]
    offset = _skip_base128(content, offset)
    transform = flags >> 6
    transformed = transform != WOFF2_NULL_TRANSFORM_OF_GLYF if tag in ("glyf", "loca") else transform != 0
    if transformed:
        offset = _skip_base128(content, offset)
    return tag.strip(), offset


def _skip_base128(content: bytes, offset: int) -> int:
    for _ in range(5):
        byte = content[offset]
        offset += 1
        if not byte & 0x80:
            return offset
    raise ValueError("a WOFF2 UIntBase128 runs past five bytes")
