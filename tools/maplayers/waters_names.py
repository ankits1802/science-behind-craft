from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from atomic_write import write_text_atomically

from .layer_files import layer_text
from .waters_register import Register, accepted_names

__all__ = [
    "WATERS_NAMES",
    "WATERS_SCHEMA_VERSION",
    "WATERS_TILES",
    "held_names",
    "register_names",
    "registered_waters",
    "reregister_files",
]

WATERS_SCHEMA_VERSION = 1
WATERS_TILES = Path("frontend/public/layers/waters")
WATERS_NAMES = Path("backend/app/data/layers/waters-names.json")
ROW_KEYS = ("id", "name", "kind", "districts")
REGISTER_KEYS = ("also", "agrees")

Tiles = Mapping[str, Mapping[str, Any]]


def register_names(name: str, districts: Sequence[int], register: Register) -> dict[str, Any]:
    agreed = register.agreeing(name, districts)
    named: dict[str, Any] = {}
    also = [held for held in accepted_names(name, agreed) if held != name]
    if also:
        named["also"] = also
    if agreed:
        named["agrees"] = [{"name": found.name, "source": found.source} for found in agreed]
    return named


def held_names(tiles: Tiles, dataset: Mapping[str, Any]) -> dict[str, Any]:
    rivers = {
        name
        for tile in tiles.values()
        for row in tile["rivers"]
        for name in (row["name"], *row.get("also", []))
    }
    dams = {row["name"] for tile in tiles.values() for row in tile["dams"]}
    return {
        "schemaVersion": WATERS_SCHEMA_VERSION,
        "datasets": [dict(dataset)],
        "rivers": sorted(rivers),
        "dams": sorted(dams),
    }


def registered_waters(
    tiles: Tiles, dataset: Mapping[str, Any], register: Register
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    named = {
        key: {**tile, "rivers": [_registered_row(row, register) for row in tile["rivers"]]}
        for key, tile in sorted(tiles.items())
    }
    return named, held_names(named, dataset)


def reregister_files(root: Path, register: Register) -> list[str]:
    folder, names_path = root / WATERS_TILES, root / WATERS_NAMES
    texts = {path.stem: path.read_text(encoding="utf-8") for path in sorted(folder.glob("*.json"))}
    dataset = json.loads(names_path.read_text(encoding="utf-8"))["datasets"][0]
    tiles, names = registered_waters(
        {key: json.loads(text) for key, text in texts.items()}, dataset, register
    )
    changed = [key for key, tile in tiles.items() if layer_text(tile) != texts[key]]
    for key in changed:
        write_text_atomically(folder / f"{key}.json", layer_text(tiles[key]))
    write_text_atomically(names_path, layer_text(names))
    return changed


def _registered_row(row: Mapping[str, Any], register: Register) -> dict[str, Any]:
    kept = {key: row[key] for key in ROW_KEYS}
    rest = {key: value for key, value in row.items() if key not in (*ROW_KEYS, *REGISTER_KEYS)}
    return kept | register_names(str(row["name"]), row["districts"], register) | rest
