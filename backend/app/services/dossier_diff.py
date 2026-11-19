from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.curation.dossier import Dossier

__all__ = ["HEADER_PARTS", "ITEM_PARTS", "NOT_IN_GIT", "WHOLE_PARTS", "dossier_changes"]

NOT_IN_GIT = "the dossier is not in git yet"
HEADER_PARTS = ("scope", "version", "curated_at", "coverage")
ITEM_PARTS = (
    "sources",
    "claims",
    "places",
    "communities",
    "stages",
    "materials",
    "tools",
    "reactions",
    "glossary",
    "open_questions",
    "pictures",
)
WHOLE_PARTS = ("searched", "environment", "market", "conflicts", "native_names", "overview")
NAMES_SHOWN = 12


def dossier_changes(exported: Dossier, git: Dossier | None) -> tuple[str, ...]:
    if git is None:
        return (NOT_IN_GIT,)
    lines = [
        f"{_alias(part)}: {_plain(getattr(git, part))} in git, {_plain(getattr(exported, part))} stored"
        for part in HEADER_PARTS
        if getattr(git, part) != getattr(exported, part)
    ]
    for part in ITEM_PARTS:
        lines += _item_changes(part, getattr(exported, part), getattr(git, part))
    lines += [
        f"{_alias(part)}: changed" for part in WHOLE_PARTS if getattr(git, part) != getattr(exported, part)
    ]
    return tuple(lines)


def _item_changes(part: str, exported: Sequence[Any], git: Sequence[Any]) -> list[str]:
    stored = {item.id: item for item in exported}
    held = {item.id: item for item in git}
    added = [key for key in stored if key not in held]
    removed = [key for key in held if key not in stored]
    changed = [
        f"{key} ({_fields(held[key], stored[key])})"
        for key in stored
        if key in held and held[key] != stored[key]
    ]
    found = [
        f"{label} {_listed(keys)}"
        for label, keys in (("added", added), ("removed", removed), ("changed", changed))
        if keys
    ]
    moved = not found and [item.id for item in exported] != [item.id for item in git]
    if moved:
        found.append("reordered")
    return [f"{_alias(part)}: {'; '.join(found)}"] if found else []


def _fields(before: Any, after: Any) -> str:
    old = before.model_dump(by_alias=True)
    new = after.model_dump(by_alias=True)
    return ", ".join(key for key in new if old.get(key) != new[key])


def _listed(keys: Sequence[str]) -> str:
    shown = ", ".join(keys[:NAMES_SHOWN])
    more = len(keys) - NAMES_SHOWN
    return f"{shown} and {more} more" if more > 0 else shown


def _alias(part: str) -> str:
    return Dossier.model_fields[part].alias or part


def _plain(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
