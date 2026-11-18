from __future__ import annotations

import copy
from typing import Any

from design.system import System

__all__ = ["clamp_css", "font_stack", "lin_val", "space_tokens", "type_tokens"]

SCRIPT_FACE_SKIPPED = {"reading": ("Aran",), "ui": ()}
SCRIPT_FACE_COLUMN = {"reading": 3, "ui": 4}


def lin_val(width: float, start: float, end: float, low: float, high: float) -> float:
    if width <= start:
        return low
    if width >= end:
        return high
    return low + (high - low) * (width - start) / (end - start)


def clamp_css(low: float, high: float, start: float, end: float) -> str:
    slope = (high - low) / (end - start)
    base = low - slope * start
    return f"clamp({low / 16:.4g}rem, calc({base / 16:.4g}rem + {slope * 100:.4g}vw * var(--text-zoom)), {high / 16:.4g}rem)"


def _script_faces(system: System, role: str) -> list[str]:
    faces: list[str] = []
    for row in system.data["scripts"]:
        face = row[SCRIPT_FACE_COLUMN[role]]
        if row[0] not in SCRIPT_FACE_SKIPPED[role] and face not in faces:
            faces.append(face)
    return faces


def font_stack(system: System, family: str) -> str:
    spec = system.data["fontStacks"][family]
    faces = [spec["primary"], *(_script_faces(system, spec["scriptFaces"]) if spec["scriptFaces"] else [])]
    return ", ".join([*(f'"{face}"' for face in faces), spec["fallback"]])


def _script_entry(row: list[Any]) -> dict[str, Any]:
    code, label, langs, reading, ui, scale, leading, display_leading, direction, note = row
    entry = {
        "label": label,
        "langs": langs,
        "reading": reading,
        "ui": ui,
        "scale": scale,
        "leading": leading,
        "displayLeading": display_leading,
        "direction": direction,
        "cssVars": {"reading": f"--font-{code.lower()}-reading", "ui": f"--font-{code.lower()}-ui"},
        "selector": f'[data-script="{code}"]',
    }
    return {**entry, "note": note} if note else entry


def _scale_sizes(system: System, row: list[Any], start: float) -> dict[str, float | None]:
    phone, high, end = row[2], row[3], row[4]
    fluid = system.data["fluid"]
    sizes: dict[str, float | None] = {"phone": phone if start <= fluid["from"] else None}
    for name, width in fluid["widths"].items():
        sizes[name] = round(lin_val(width, start, end, phone, high), 1) if width >= start else None
    return sizes


def _scale_entry(system: System, row: list[Any]) -> dict[str, Any]:
    name, family, phone, high, end, leading, tracking, weight, use = row
    fluid = system.data["fluid"]
    start = fluid["numeralFrom"] if name == "numeral" else fluid["from"]
    sizes = _scale_sizes(system, row, start)
    return {
        "cssVar": f"--text-{name}",
        "family": family,
        **sizes,
        "fluidRange": [start, end],
        "value": clamp_css(phone, high, start, end) if phone != high else f"{phone / 16:.4g}rem",
        "lineHeight": round(leading, 3),
        "tracking": f"{tracking}em",
        "weight": weight,
        "use": use,
        "larger": {key: (round(size * fluid["larger"], 1) if size else None) for key, size in sizes.items()},
    }


def type_tokens(system: System) -> dict[str, Any]:
    tokens = copy.deepcopy(system.data["type"])
    for family, spec in tokens["families"].items():
        spec["stack"] = font_stack(system, family)
    for row in system.data["scripts"]:
        tokens["scripts"][row[0]] = _script_entry(row)
    tokens["scripts"]["rules"] = system.data["scriptRules"]
    for row in system.data["typeScale"]:
        tokens["scale"][row[0]] = _scale_entry(system, row)
    return tokens


def space_tokens(system: System) -> dict[str, Any]:
    space: dict[str, Any] = {
        f"space-{i + 1}": {"px": px, "rem": f"{px / 16:g}rem"} for i, px in enumerate(system.data["space"])
    }
    section = system.data["spaceSection"]
    space["section"] = {
        "value": clamp_css(section["min"], section["max"], section["from"], section["to"]),
        "use": section["use"],
    }
    space["stack"] = system.data["spaceStack"]
    return space
