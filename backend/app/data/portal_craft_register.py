from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .craft_master_loader import ACTIVE, DATA_DIR, MERGED

__all__ = ["PORTAL_CRAFTS_FILE", "PortalCraft", "load_portal_crafts", "parse_portal_crafts"]

PORTAL_CRAFTS_FILE = DATA_DIR / "portal_craft_register.json"
REGISTER_STATUSES = (ACTIVE, MERGED)


@dataclass(frozen=True)
class PortalCraft:
    slug: str
    name: str
    sub_category_slug: str | None
    state_of_origin: tuple[str, ...]
    state_of_practice: tuple[str, ...]
    gi_status: str | None
    portals: tuple[str, ...]
    status: str
    merged_into: str | None


def parse_portal_crafts(raw: Mapping[str, Any]) -> tuple[PortalCraft, ...]:
    crafts = tuple(
        PortalCraft(
            slug=row["slug"],
            name=row["name"],
            sub_category_slug=row.get("subCategorySlug"),
            state_of_origin=tuple(row["stateOfOrigin"]),
            state_of_practice=tuple(row["stateOfPractice"]),
            gi_status=row.get("giStatus"),
            portals=tuple(row["portals"]),
            status=row["status"],
            merged_into=row.get("mergedInto"),
        )
        for row in raw["crafts"]
    )
    for craft in crafts:
        if craft.status not in REGISTER_STATUSES:
            raise ValueError(f"portal craft {craft.slug} has status {craft.status}")
        if (craft.status == MERGED) != (craft.merged_into is not None):
            raise ValueError(f"portal craft {craft.slug}: a MERGED craft, and only one, names mergedInto")
    return crafts


@lru_cache(maxsize=1)
def load_portal_crafts() -> tuple[PortalCraft, ...]:
    return parse_portal_crafts(json.loads(PORTAL_CRAFTS_FILE.read_text(encoding="utf-8")))
