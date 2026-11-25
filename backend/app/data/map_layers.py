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
    "RELIEF_FILE",
    "RIVERS_FILE",
    "HeldShapes",
    "held_river_names",
    "held_shapes",
]

LAYERS_DIR = DATA_DIR / "layers"
RELIEF_FILE = "relief.json"
RIVERS_FILE = "rivers.json"
MINERALS_FILE = "minerals.json"
LAYER_FILES = (RELIEF_FILE, RIVERS_FILE, MINERALS_FILE)
DISTRICT_SHAPES_FILE = DATA_DIR / "district-shapes.json"


@dataclass(frozen=True)
class HeldShapes:
    districts: frozenset[int]
    states: frozenset[int]


@cache
def held_shapes() -> HeldShapes:
    body = json.loads(DISTRICT_SHAPES_FILE.read_text(encoding="utf-8"))
    rows = body["districts"]
    return HeldShapes(
        districts=frozenset(int(row["lgd"]) for row in rows),
        states=frozenset(int(row["stateLgd"]) for row in rows),
    )


@cache
def held_river_names() -> frozenset[str]:
    body = json.loads((LAYERS_DIR / RIVERS_FILE).read_text(encoding="utf-8"))
    return frozenset(str(label["text"]) for label in body["labels"])
