from __future__ import annotations

import struct
from pathlib import PurePosixPath

from hygiene.fonts import font_tables, font_violations

GLYF_INDEX = 10
LOCA_INDEX = 11
PREP_INDEX = 12
GASP_INDEX = 17
FVAR_INDEX = 47
CFF_INDEX = 13


def woff2(entries: list[bytes]) -> bytes:
    header = b"wOF2" + b"\x00\x01\x00\x00" + struct.pack(">IHH", 0, len(entries), 0) + bytes(32)
    return header + b"".join(entries)


def known(index: int, length: int = 0x20) -> bytes:
    return bytes([index, length])


def transformed_glyf() -> bytes:
    return bytes([GLYF_INDEX, 0x81, 0x00, 0x40])


def transformed_loca() -> bytes:
    return bytes([LOCA_INDEX, 0x10, 0x00])


def arbitrary(tag: bytes) -> bytes:
    return bytes([63]) + tag + bytes([0x08])


def sfnt(tags: list[bytes]) -> bytes:
    return b"\x00\x01\x00\x00" + struct.pack(">HHHH", len(tags), 0, 0, 0) + b"".join(tag + bytes(12) for tag in tags)


def violations(name: str, content: bytes) -> list[str]:
    return [violation.describe() for violation in font_violations([(PurePosixPath(name), content)])]


def test_woff2_tables_are_read_past_transformed_glyf_and_loca() -> None:
    content = woff2([known(GASP_INDEX), transformed_glyf(), transformed_loca(), known(PREP_INDEX), known(FVAR_INDEX)])
    assert font_tables(PurePosixPath("frontend/fonts/a.woff2"), content) == {"gasp", "glyf", "loca", "prep", "fvar"}


def test_woff2_arbitrary_tags_are_read() -> None:
    content = woff2([arbitrary(b"STAT"), known(CFF_INDEX)])
    assert font_tables(PurePosixPath("frontend/fonts/a.woff2"), content) == {"STAT", "CFF"}


def test_a_web_font_with_outlines_and_no_prep_is_refused() -> None:
    content = woff2([known(GASP_INDEX), transformed_glyf(), transformed_loca(), known(FVAR_INDEX)])
    found = violations("frontend/fonts/newsreader-latin-var.woff2", content)
    assert len(found) == 1
    assert found[0].startswith("frontend/fonts/newsreader-latin-var.woff2: has TrueType outlines but no prep table")


def test_a_web_font_with_prep_passes() -> None:
    content = woff2([known(GASP_INDEX), transformed_glyf(), transformed_loca(), known(PREP_INDEX)])
    assert violations("frontend/fonts/a.woff2", content) == []


def test_a_postscript_outline_font_needs_no_prep() -> None:
    assert violations("frontend/fonts/a.woff2", woff2([known(CFF_INDEX), known(GASP_INDEX)])) == []


def test_a_truetype_file_is_read_from_its_table_records() -> None:
    assert violations("frontend/public/a.ttf", sfnt([b"glyf", b"loca", b"head"])) != []
    assert violations("frontend/public/a.ttf", sfnt([b"glyf", b"loca", b"prep"])) == []


def test_a_web_font_that_cannot_be_read_is_refused() -> None:
    assert violations("frontend/fonts/a.woff2", b"\x00\x01\r\n") == [
        "frontend/fonts/a.woff2: cannot be read as a font: not a WOFF2 file: the signature is not wOF2"
    ]
    assert violations("frontend/fonts/b.woff2", b"wOF2\x00") != []


def test_fonts_outside_the_web_client_are_not_checked() -> None:
    assert violations("backend/app/data/exports/fonts/NotoSans-Regular.ttf", sfnt([b"glyf", b"loca"])) == []
