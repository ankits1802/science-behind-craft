from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from basemap.polyline import india_payload

from .layer_files import layer_text

__all__ = [
    "BASE_BOUNDARIES",
    "BASE_FILES",
    "INDIA_SOURCE",
    "MEASURED_FILES",
    "MEASURED_OUTPUT",
    "OUTLINE_FILE",
    "mirror_base",
    "mirror_measured",
    "outline_text",
    "unmirrored",
    "unmirrored_base",
]

MEASURED_OUTPUT = Path("backend/app/data/layers")
MEASURED_FILES = ("relief.json", "rivers.json", "minerals.json")
BASE_BOUNDARIES = Path("frontend/public/boundaries")
BASE_FILES = ("state-borders.json",)
INDIA_SOURCE = Path("frontend/components/map/indiaGeometry.ts")
OUTLINE_FILE = "india-outline.json"
OUTLINE_SCHEMA_VERSION = 1


def mirror_measured(drawn: Path, measured: Path, names: Iterable[str] = MEASURED_FILES) -> list[Path]:
    measured.mkdir(parents=True, exist_ok=True)
    written = []
    for name in names:
        target = measured / name
        target.write_bytes((drawn / name).read_bytes())
        written.append(target)
    return written


def unmirrored(drawn: Path, measured: Path, names: Iterable[str] = MEASURED_FILES) -> list[str]:
    return [
        name
        for name in names
        if not (measured / name).is_file() or (measured / name).read_bytes() != (drawn / name).read_bytes()
    ]


def outline_text(india_source: str) -> str:
    return layer_text({"schemaVersion": OUTLINE_SCHEMA_VERSION, "payload": india_payload(india_source)})


def mirror_base(root: Path) -> list[Path]:
    measured = root / MEASURED_OUTPUT
    written = mirror_measured(root / BASE_BOUNDARIES, measured, BASE_FILES)
    outline = measured / OUTLINE_FILE
    outline.write_text(
        outline_text((root / INDIA_SOURCE).read_text(encoding="utf-8")), encoding="utf-8", newline="\n"
    )
    return [*written, outline]


def unmirrored_base(root: Path) -> list[str]:
    measured = root / MEASURED_OUTPUT
    stale = unmirrored(root / BASE_BOUNDARIES, measured, BASE_FILES)
    outline = measured / OUTLINE_FILE
    expected = outline_text((root / INDIA_SOURCE).read_text(encoding="utf-8"))
    if not outline.is_file() or outline.read_text(encoding="utf-8") != expected:
        stale.append(OUTLINE_FILE)
    return stale
