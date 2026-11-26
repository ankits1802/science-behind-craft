from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from typing import Any

__all__ = ["described", "description_problems", "missing_title", "untyped"]

DATA_KEYS = frozenset({"default", "const", "enum", "examples"})
SCHEMA_MAPS = ("properties", "patternProperties", "$defs")
POINTERS = re.compile(
    r"\b(?:guides?|playbook|cookbook|skills?|next_step)\b|kalavigyan://(?!components/)", re.IGNORECASE
)
ADDRESS = re.compile(r"\b[a-z][a-z0-9-]*/[1-9][0-9]*\b")
ADDRESSED = re.compile(r"\b(?:you|your|yours|yourself)\b", re.IGNORECASE)
ORDER = re.compile(r"\bfirst\b(?! (?:frame|sheet|screen)\b)", re.IGNORECASE)
SENTENCE_START = re.compile(r"(?:^|[.!?;:]\s+|\(\s*)([A-Z][a-z]+)\b")
AFTER_COLON = re.compile(r":\s+([a-z]+)\b")
IMPERATIVES = frozenset(
    {
        "Add",
        "Allow",
        "Always",
        "Ask",
        "Avoid",
        "Build",
        "Call",
        "Check",
        "Choose",
        "Cite",
        "Compose",
        "Copy",
        "Deliver",
        "Do",
        "Draw",
        "Fill",
        "Find",
        "Fix",
        "Follow",
        "Get",
        "Give",
        "Go",
        "Keep",
        "Leave",
        "Let",
        "List",
        "Load",
        "Look",
        "Make",
        "Name",
        "Never",
        "Open",
        "Pass",
        "Place",
        "Prefer",
        "Preview",
        "Propose",
        "Put",
        "Quote",
        "Read",
        "Remember",
        "Reserve",
        "Run",
        "Say",
        "Search",
        "See",
        "Send",
        "Show",
        "Start",
        "Tell",
        "Test",
        "Try",
        "Use",
        "Wait",
        "Write",
    }
)


def description_problems(text: str, own: str, tools: Iterable[str]) -> list[str]:
    found = [
        f"names the tool {name}" for name in sorted(set(tools) - {own}) if re.search(rf"\b{name}\b", text)
    ]
    found += [f"points to {match.group(0)}" for match in POINTERS.finditer(text)]
    found += [f"points to {match.group(0)}" for match in ADDRESS.finditer(text)]
    found += [f"addresses the model as {match.group(0)}" for match in ADDRESSED.finditer(text)]
    found += [f"orders the calls with {match.group(0)}" for match in ORDER.finditer(text)]
    found += [
        f"opens a sentence with the order {match.group(1)}"
        for match in SENTENCE_START.finditer(text)
        if match.group(1) in IMPERATIVES
    ]
    found += [
        f"opens a clause with the order {match.group(1)}"
        for match in AFTER_COLON.finditer(text)
        if match.group(1).capitalize() in IMPERATIVES
    ]
    return found


def described(tool: Mapping[str, Any]) -> Iterator[tuple[str, str]]:
    yield tool["name"], tool["description"]
    yield from _descriptions(tool["inputSchema"], tool["name"])


def untyped(node: Any, where: str = "schema") -> list[str]:
    if isinstance(node, list):
        return [found for item in node for found in untyped(item, where)]
    if not isinstance(node, dict):
        return []
    found: list[str] = []
    for key, value in node.items():
        if key in DATA_KEYS:
            continue
        if key in SCHEMA_MAPS and isinstance(value, dict):
            for name, child in value.items():
                if key != "$defs" and not (isinstance(child, dict) and "type" in child):
                    found.append(f"{where}.{name}")
                found += untyped(child, f"{where}.{name}")
        else:
            found += untyped(value, where)
    return found


def missing_title(tool: Mapping[str, Any]) -> bool:
    annotations = tool.get("annotations") or {}
    title = annotations.get("title")
    return not isinstance(title, str) or not title.strip() or title != tool.get("title")


def _descriptions(node: Any, where: str) -> Iterator[tuple[str, str]]:
    if isinstance(node, list):
        for item in node:
            yield from _descriptions(item, where)
        return
    if not isinstance(node, dict):
        return
    if isinstance(node.get("description"), str):
        yield where, node["description"]
    for key, value in node.items():
        if key in DATA_KEYS or key == "description":
            continue
        if key in SCHEMA_MAPS and isinstance(value, dict):
            for name, child in value.items():
                yield from _descriptions(child, f"{where}.{name}")
        else:
            yield from _descriptions(value, where)
