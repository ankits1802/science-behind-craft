from __future__ import annotations

import json
from typing import Any

from .dossier import Dossier

__all__ = ["ALWAYS_WRITTEN", "dossier_text"]

ALWAYS_WRITTEN = ("schemaVersion", "curator")
CURATED_AT = "curatedAt"
INDENT = 2


def dossier_text(dossier: Dossier, *, like: str | None = None) -> str:
    full = dossier.model_dump(mode="json", by_alias=True)
    kept = dossier.model_dump(mode="json", by_alias=True, exclude_defaults=True)
    for key in ALWAYS_WRITTEN:
        kept.setdefault(key, full[key])
    kept[CURATED_AT] = full[CURATED_AT] = dossier.curated_at.isoformat()
    data = _shaped(full, kept, _plain(like))
    return json.dumps(data, ensure_ascii=False, indent=_indent(like)) + "\n"


def _plain(text: str | None) -> Any:
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def _indent(text: str | None) -> int:
    lines = (text or "").splitlines()
    second = lines[1] if len(lines) > 1 else ""
    return len(second) - len(second.lstrip(" ")) or INDENT


def _shaped(full: Any, kept: Any, like: Any) -> Any:
    if isinstance(full, dict):
        guide = like if isinstance(like, dict) else {}
        held = kept if isinstance(kept, dict) else {}
        keys = [key for key in guide if key in full]
        keys += [key for key in full if key not in guide and key in held]
        return {key: _shaped(full[key], held.get(key, _bare(full[key])), guide.get(key)) for key in keys}
    if isinstance(full, list):
        guide_items = like if isinstance(like, list) else []
        held_items = kept if isinstance(kept, list) and len(kept) == len(full) else full
        return [
            _shaped(item, held_items[index], guide_items[index] if index < len(guide_items) else None)
            for index, item in enumerate(full)
        ]
    return full


def _bare(value: Any) -> Any:
    return {} if isinstance(value, dict) else value
