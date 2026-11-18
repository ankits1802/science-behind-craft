from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

REPO_ROOT = Path(__file__).resolve().parents[2]
FONTS = REPO_ROOT / "frontend" / "fonts"
LATIN_SIZE = 100.0
DEVANAGARI_SCALE = 1.08
GAP = 43.0
RULE_WIDTH = 5.0
LATIN_TRACKING = -20
DEVANAGARI_BASELINE = 93.0


@dataclass(frozen=True)
class Run:
    font: str
    axes: dict[str, float]
    text: str
    script: str
    language: str


LATIN = Run("newsreader-latin-var.woff2", {"wght": 600, "opsz": 24}, "KalaVigyan", "Latn", "en")
DEVANAGARI = Run("noto-serif-devanagari-var.woff2", {"wght": 500}, "कलाविज्ञान", "Deva", "hi")


def instance(run: Run) -> tuple[TTFont, bytes]:
    font = instancer.instantiateVariableFont(TTFont(FONTS / run.font), run.axes)
    font.flavor = None
    buffer = BytesIO()
    font.save(buffer)
    data = buffer.getvalue()
    return TTFont(BytesIO(data)), data


def shaped(run: Run, data: bytes) -> hb.Buffer:
    buffer = hb.Buffer()
    buffer.add_str(run.text)
    buffer.guess_segment_properties()
    buffer.script = run.script
    buffer.language = run.language
    hb.shape(hb.Font(hb.Face(data)), buffer, {"kern": True, "liga": True})
    return buffer


def outline(run: Run, *, size: float, origin: tuple[float, float], tracking: int = 0) -> tuple[str, float]:
    font, data = instance(run)
    scale = size / font["head"].unitsPerEm
    glyphs = font.getGlyphSet()
    order = font.getGlyphOrder()
    pen = SVGPathPen(glyphs, ntos=lambda value: f"{value:.2f}".rstrip("0").rstrip("."))
    advance = 0
    buffer = shaped(run, data)
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions, strict=True):
        x = origin[0] + (advance + position.x_offset) * scale
        y = origin[1] - position.y_offset * scale
        glyphs[order[info.codepoint]].draw(TransformPen(pen, (scale, 0, 0, -scale, x, y)))
        advance += position.x_advance + tracking
    return pen.getCommands(), advance * scale


def lockup() -> dict[str, object]:
    latin, latin_width = outline(LATIN, size=LATIN_SIZE, origin=(0.0, LATIN_SIZE), tracking=LATIN_TRACKING)
    rule_x = latin_width + GAP
    devanagari_x = rule_x + RULE_WIDTH + GAP
    devanagari, width = outline(
        DEVANAGARI, size=LATIN_SIZE * DEVANAGARI_SCALE, origin=(devanagari_x, DEVANAGARI_BASELINE)
    )
    return {
        "latin": latin,
        "devanagari": devanagari,
        "ruleX": round(rule_x, 2),
        "width": round(devanagari_x + width, 2),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SVG outlines of the KalaVigyan wordmark from the self-hosted fonts."
    )
    parser.add_argument("--out", type=Path, required=True, help="JSON file to write")
    options = parser.parse_args(argv)
    options.out.write_text(json.dumps(lockup(), ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
