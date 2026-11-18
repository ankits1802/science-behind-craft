from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import Any

from .craft_master_loader import DATA_DIR, MasterCraft, load_master

__all__ = [
    "CRAFT_NAMES_FILE",
    "CRAFT_NAMES_SCHEMA_VERSION",
    "CraftNameEdits",
    "load_craft_names",
    "parse_craft_names",
]

CRAFT_NAMES_FILE = DATA_DIR / "craft_names.json"
CRAFT_NAMES_SCHEMA_VERSION = 1
NAME_EDITS = frozenset({"displayName", "localName"})


@dataclass(frozen=True)
class CraftNameEdits:
    display_names: Mapping[str, str]
    local_names: Mapping[str, str | None]

    def display_name(self, craft_slug: str, name: str) -> str:
        return self.display_names.get(craft_slug, name)

    def sets_local_name(self, craft_slug: str) -> bool:
        return craft_slug in self.local_names

    def local_name(self, craft_slug: str) -> str | None:
        return self.local_names.get(craft_slug)


def parse_craft_names(raw: Mapping[str, Any], master: Sequence[MasterCraft]) -> CraftNameEdits:
    if raw.get("schemaVersion") != CRAFT_NAMES_SCHEMA_VERSION:
        raise ValueError(f"craft names need schemaVersion {CRAFT_NAMES_SCHEMA_VERSION}")
    crafts = {craft.slug: craft for craft in master}
    display: dict[str, str] = {}
    local: dict[str, str | None] = {}
    for slug, edits in (raw.get("crafts") or {}).items():
        craft = crafts.get(slug)
        if craft is None or not edits or not set(edits) <= NAME_EDITS:
            raise ValueError(f"craft names: {slug!r} is not a master craft, or edits an unknown field")
        if "displayName" in edits:
            display[slug] = _display_name(craft, edits["displayName"])
        if "localName" in edits:
            local[slug] = None if edits["localName"] is None else _text(edits["localName"], slug)
    return CraftNameEdits(display_names=MappingProxyType(display), local_names=MappingProxyType(local))


@lru_cache(maxsize=1)
def load_craft_names() -> CraftNameEdits:
    return parse_craft_names(json.loads(CRAFT_NAMES_FILE.read_text(encoding="utf-8")), load_master())


def _display_name(craft: MasterCraft, value: Any) -> str:
    shown = _text(value, craft.slug)
    if craft.is_catch_all:
        raise ValueError(f"{craft.slug} is a catch-all row; it is shown by its kind's other name")
    if shown == craft.name:
        raise ValueError(f"the display name of {craft.slug} repeats its master name")
    return shown


def _text(value: Any, owner: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"craft names: the name given for {owner} is empty or carries outer spaces")
    return value
