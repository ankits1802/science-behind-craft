from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from types import MappingProxyType

from app.data.craft_master_loader import DATA_DIR

__all__ = ["MONOGRAPHS_DIR", "monograph_layouts"]

MONOGRAPHS_DIR = DATA_DIR / "monographs"
CONTENT_FILE = "content.json"
LAYOUT_KEY = "layout"


@lru_cache(maxsize=1)
def monograph_layouts() -> Mapping[str, bool]:
    found = {}
    for folder in sorted(MONOGRAPHS_DIR.iterdir()):
        content = folder / CONTENT_FILE
        if folder.is_dir() and content.is_file():
            layout = json.loads(content.read_bytes().decode("utf-8")).get(LAYOUT_KEY)
            found[folder.name] = isinstance(layout, list) and bool(layout)
    return MappingProxyType(found)
