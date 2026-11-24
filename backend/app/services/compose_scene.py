from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .compose_held import CraftHeld, HeldReaction, HeldSpecies, HeldStage
from .compose_parts import material_named

__all__ = ["reaction_scene"]

SCENE_WIDTH = 640
SCENE_HEIGHT = 180
SCENE_MARGIN = 40
SWATCH_MAX = 64
SWATCH_GAP = 12
ARROW_WIDTH = 72
OFF = "off"
INK = "var(--ink-2)"
ARROW_INK = "var(--ink-3)"
GROUND = "var(--sunk)"
OUTLINE_FILL = "var(--raised)"
UNRECORDED_DASH = "6 4"

Node = dict[str, Any]
Played = tuple[HeldReaction, HeldStage | None]


def reaction_scene(craft: CraftHeld, played: Sequence[Played], current: int) -> Node:
    groups = [
        _step_group(craft, reaction, step, current) for step, (reaction, _) in enumerate(played, start=1)
    ]
    attrs = {
        "class": "scene",
        "viewBox": f"0 0 {SCENE_WIDTH} {SCENE_HEIGHT}",
        "aria-hidden": "true",
        "focusable": "false",
    }
    ground = _rect(0, 0, (SCENE_WIDTH, SCENE_HEIGHT), {"fill": GROUND})
    return {"tag": "svg", "attrs": attrs, "children": [ground, *groups]}


def _step_group(craft: CraftHeld, reaction: HeldReaction, step: int, current: int) -> Node:
    sides = (reaction.reactants, reaction.products)
    count = len(sides[0]) + len(sides[1])
    room = SCENE_WIDTH - 2 * SCENE_MARGIN - ARROW_WIDTH - SWATCH_GAP * (count - 1)
    size = min(SWATCH_MAX, room / count)
    top = (SCENE_HEIGHT - size) / 2
    x = (SCENE_WIDTH - (count * size + SWATCH_GAP * (count - 1) + ARROW_WIDTH)) / 2
    children: list[Node] = []
    for at, side in enumerate(sides):
        for species in side:
            children.append(_swatch(craft, species, (x, top), size))
            x += size + SWATCH_GAP
        if at == 0:
            children += _arrow(x - SWATCH_GAP / 2, SCENE_HEIGHT / 2)
            x += ARROW_WIDTH
    attrs = {"data-on": str(step)} | ({} if step == current else {"class": OFF})
    return {"tag": "g", "attrs": attrs, "children": children}


def _swatch(craft: CraftHeld, species: HeldSpecies, at: tuple[float, float], size: float) -> Node:
    material = material_named(craft, species.name)
    paint = {"fill": OUTLINE_FILL, "stroke": INK, "stroke-width": "1.5"}
    if material is None or not material.tokens:
        paint["stroke-dasharray"] = UNRECORDED_DASH
    return _rect(at[0], at[1], (size, size), {"rx": "4", **paint})


def _arrow(x: float, y: float) -> list[Node]:
    start, end = x + 12, x + ARROW_WIDTH - 12
    line = {
        "x1": _n(start),
        "y1": _n(y),
        "x2": _n(end - 8),
        "y2": _n(y),
        "stroke": ARROW_INK,
        "stroke-width": "2",
    }
    head = f"{_n(end)},{_n(y)} {_n(end - 10)},{_n(y - 6)} {_n(end - 10)},{_n(y + 6)}"
    return [{"tag": "line", "attrs": line}, {"tag": "polygon", "attrs": {"points": head, "fill": ARROW_INK}}]


def _rect(x: float, y: float, size: tuple[float, float], paint: dict[str, str]) -> Node:
    box = {"x": _n(x), "y": _n(y), "width": _n(size[0]), "height": _n(size[1])}
    return {"tag": "rect", "attrs": box | paint}


def _n(value: float) -> str:
    rounded = round(value, 1)
    return str(int(rounded)) if rounded == int(rounded) else str(rounded)
