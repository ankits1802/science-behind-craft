from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache

from .craft_master_loader import DATA_DIR

__all__ = [
    "DISTRICT_SHAPES_FILE",
    "LAYERS_DIR",
    "LAYER_FILES",
    "MINERALS_FILE",
    "OUTLINE_FILE",
    "RELIEF_FILE",
    "RIVERS_FILE",
    "STATE_BORDERS_FILE",
    "WATERS_NAMES_FILE",
    "WATERS_SCHEMA_VERSION",
    "BaseFiles",
    "HeldShapes",
    "held_base",
    "held_dam_names",
    "held_river_names",
    "held_shapes",
]

LAYERS_DIR = DATA_DIR / "layers"
RELIEF_FILE = "relief.json"
RIVERS_FILE = "rivers.json"
MINERALS_FILE = "minerals.json"
WATERS_NAMES_FILE = "waters-names.json"
OUTLINE_FILE = "india-outline.json"
STATE_BORDERS_FILE = "state-borders.json"
WATERS_SCHEMA_VERSION = 1
BASE_SCHEMA_VERSION = 1
LAYER_FILES = (RELIEF_FILE, RIVERS_FILE, MINERALS_FILE)
DISTRICT_SHAPES_FILE = DATA_DIR / "district-shapes.json"


@dataclass(frozen=True)
class HeldShapes:
    districts: frozenset[int]
    states: frozenset[int]


@dataclass(frozen=True)
class BaseFiles:
    outline: str
    states: str
    districts: tuple[tuple[int, int, tuple[str, ...]], ...]


@cache
def held_base() -> BaseFiles:
    outline = _versioned(OUTLINE_FILE)
    states = _versioned(STATE_BORDERS_FILE)
    shapes = json.loads(DISTRICT_SHAPES_FILE.read_text(encoding="utf-8"))["districts"]
    return BaseFiles(
        outline=str(outline["payload"]),
        states=str(states["lines"]),
        districts=tuple(
            (int(row["lgd"]), int(row["stateLgd"]), tuple(str(ring) for ring in row["rings"]))
            for row in shapes
        ),
    )


def _versioned(name: str) -> dict[str, object]:
    body = json.loads((LAYERS_DIR / name).read_text(encoding="utf-8"))
    if body.get("schemaVersion") != BASE_SCHEMA_VERSION:
        raise ValueError(f"{name} is schema version {BASE_SCHEMA_VERSION}")
    return body


@cache
def held_shapes() -> HeldShapes:
    body = json.loads(DISTRICT_SHAPES_FILE.read_text(encoding="utf-8"))
    rows = body["districts"]
    return HeldShapes(
        districts=frozenset(int(row["lgd"]) for row in rows),
        states=frozenset(int(row["stateLgd"]) for row in rows),
    )


@cache
def _waters_names() -> dict[str, list[str]]:
    body = json.loads((LAYERS_DIR / WATERS_NAMES_FILE).read_text(encoding="utf-8"))
    if body.get("schemaVersion") != WATERS_SCHEMA_VERSION:
        raise ValueError(f"{WATERS_NAMES_FILE} is schema version {WATERS_SCHEMA_VERSION}")
    return {"rivers": [str(name) for name in body["rivers"]], "dams": [str(name) for name in body["dams"]]}


@cache
def held_river_names() -> frozenset[str]:
    body = json.loads((LAYERS_DIR / RIVERS_FILE).read_text(encoding="utf-8"))
    labels = frozenset(str(label["text"]) for label in body["labels"])
    return labels | frozenset(_waters_names()["rivers"])


@cache
def held_dam_names() -> frozenset[str]:
    return frozenset(_waters_names()["dams"])
