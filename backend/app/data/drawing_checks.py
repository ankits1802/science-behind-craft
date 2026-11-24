from __future__ import annotations

from functools import cache

from .craft_master_loader import DATA_DIR

__all__ = ["DRAWING_CHECKS_PATH", "DRAWING_KIT", "drawing_checks"]

DRAWING_CHECKS_PATH = DATA_DIR / "design" / "drawing-checks.js"
DRAWING_KIT = "globalThis.kvDrawing"


@cache
def drawing_checks() -> str:
    return DRAWING_CHECKS_PATH.read_bytes().decode("utf-8")
