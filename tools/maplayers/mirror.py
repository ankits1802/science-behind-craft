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
    "WATERS_INDEX",
    "WATERS_TILES",
    "mirror_base",
    "mirror_measured",
    "mirror_waters",
    "outline_text",
    "unmirrored",
    "unmirrored_base",
    "unmirrored_waters",
]

MEASURED_OUTPUT = Path("backend/app/data/layers")
MEASURED_FILES = ("relief.json", "rivers.json", "minerals.json")
BASE_BOUNDARIES = Path("frontend/public/boundaries")
BASE_FILES = ("state-borders.json",)
INDIA_SOURCE = Path("frontend/components/map/indiaGeometry.ts")
OUTLINE_FILE = "india-outline.json"
OUTLINE_SCHEMA_VERSION = 1
DRAWN_LAYERS = Path("frontend/public/layers")
WATERS_INDEX = "waters.json"
WATERS_TILES = "waters"


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


def mirror_waters(root: Path) -> list[Path]:
    drawn, measured = root / DRAWN_LAYERS, root / MEASURED_OUTPUT
    written = mirror_measured(drawn, measured, (WATERS_INDEX,))
    tiles = measured / WATERS_TILES
    tiles.mkdir(parents=True, exist_ok=True)
    names = _tile_names(drawn)
    for stale in tiles.glob("*.json"):
        if stale.name not in names:
            stale.unlink()
    return [*written, *mirror_measured(drawn / WATERS_TILES, tiles, names)]


def unmirrored_waters(root: Path) -> list[str]:
    drawn, measured = root / DRAWN_LAYERS, root / MEASURED_OUTPUT
    names = _tile_names(drawn)
    held = {path.name for path in (measured / WATERS_TILES).glob("*.json")}
    stale = unmirrored(drawn / WATERS_TILES, measured / WATERS_TILES, names)
    return [
        *unmirrored(drawn, measured, (WATERS_INDEX,)),
        *(f"{WATERS_TILES}/{name}" for name in stale),
        *(f"{WATERS_TILES}/{name}" for name in sorted(held - set(names))),
    ]


def _tile_names(drawn: Path) -> tuple[str, ...]:
    return tuple(sorted(path.name for path in (drawn / WATERS_TILES).glob("*.json")))
