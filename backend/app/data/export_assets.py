from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import MappingProxyType

__all__ = [
    "APA_STYLE_ID",
    "APA_STYLE_UPDATED",
    "EXPORTS_DIR",
    "REVEAL_VERSION",
    "SCRIPT_FONT_FAMILIES",
    "FontFiles",
    "apa_style_path",
    "font_files",
    "reveal_licence",
    "reveal_script",
    "reveal_styles",
]

EXPORTS_DIR = Path(__file__).resolve().parent / "exports"
REVEAL_VERSION = "6.0.2"
APA_STYLE_ID = "http://www.zotero.org/styles/apa"
APA_STYLE_UPDATED = "2026-02-07T00:00:00+00:00"
SCRIPT_FONT_FAMILIES: Mapping[str, str] = MappingProxyType(
    {
        "Latn": "NotoSans",
        "Deva": "NotoSansDevanagari",
        "Beng": "NotoSansBengali",
        "Taml": "NotoSansTamil",
        "Telu": "NotoSansTelugu",
        "Gujr": "NotoSansGujarati",
        "Knda": "NotoSansKannada",
        "Mlym": "NotoSansMalayalam",
        "Orya": "NotoSansOriya",
        "Guru": "NotoSansGurmukhi",
        "Arab": "NotoNaskhArabic",
    }
)


@dataclass(frozen=True)
class FontFiles:
    family: str
    regular: Path
    bold: Path


def font_files(script: str) -> FontFiles:
    family = SCRIPT_FONT_FAMILIES.get(script)
    if family is None:
        raise ValueError(f"no vendored font draws the {script} script")
    folder = EXPORTS_DIR / "fonts"
    return FontFiles(
        family=family, regular=folder / f"{family}-Regular.ttf", bold=folder / f"{family}-Bold.ttf"
    )


def apa_style_path() -> Path:
    return EXPORTS_DIR / "csl" / "apa.csl"


@cache
def reveal_script() -> str:
    return _vendored("reveal/reveal.js")


@cache
def reveal_styles() -> str:
    return _vendored("reveal/reveal.css")


@cache
def reveal_licence() -> str:
    return _vendored("reveal/LICENSE.txt")


def _vendored(relative: str) -> str:
    return (EXPORTS_DIR / relative).read_text(encoding="utf-8")
