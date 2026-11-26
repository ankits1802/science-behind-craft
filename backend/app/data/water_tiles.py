from __future__ import annotations

import json
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Any

from .map_layers import LAYERS_DIR, WATERS_SCHEMA_VERSION

__all__ = [
    "WATERS_INDEX_FILE",
    "WATERS_TILES_DIR",
    "held_water_tile",
    "held_waters_index",
]

WATERS_INDEX_FILE = "waters.json"
WATERS_TILES_DIR = "waters"
TILE_KEYS = ("tile", "bounds", "rivers", "dams")


@cache
def held_waters_index() -> Mapping[str, Any]:
    body = _versioned(LAYERS_DIR / WATERS_INDEX_FILE, WATERS_INDEX_FILE)
    if not isinstance(body.get("tiles"), list) or not isinstance(body.get("datasets"), list):
        raise ValueError(f"{WATERS_INDEX_FILE} lists no tiles or no datasets")
    return body


@cache
def held_water_tile(tile_id: str) -> Mapping[str, Any]:
    known = {str(row["id"]) for row in held_waters_index()["tiles"]}
    if tile_id not in known:
        raise ValueError(f"the small waters hold no tile {tile_id}")
    name = f"{WATERS_TILES_DIR}/{tile_id}.json"
    body = _versioned(LAYERS_DIR / WATERS_TILES_DIR / f"{tile_id}.json", name)
    missing = [key for key in TILE_KEYS if key not in body]
    if missing or body["tile"] != tile_id:
        raise ValueError(f"{name} is not the tile {tile_id}: it lacks {', '.join(missing) or 'its own id'}")
    return body


def _versioned(path: Path, name: str) -> dict[str, Any]:
    body = json.loads(path.read_text(encoding="utf-8"))
    if body.get("schemaVersion") != WATERS_SCHEMA_VERSION:
        raise ValueError(f"{name} is not schema version {WATERS_SCHEMA_VERSION}")
    return body
