from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.research.component_specs_kit import DeclaredDiagramSpec, KitPartSpec

from .export_still_kit_more import heat_nodes, tool_nodes, water_nodes
from .export_still_kit_parts import (
    bath_nodes,
    block_nodes,
    cloth_nodes,
    paste_nodes,
    piece_nodes,
    section_nodes,
)
from .export_still_kit_surfaces import INK, Node, group, path
from .export_still_svg import svg_still
from .export_stills import Affine, Still, StillText, ink, merged, translated

__all__ = [
    "ARROW_LAYOUTS",
    "KIT_SCENE_MARK",
    "PANELS_ACROSS",
    "diagram_still",
    "kit_scene_parts",
    "part_still",
    "scene_still",
]

KIT_SCENE_MARK = "parts"
PART_BOX = 120.0
PANEL_WIDTH, PANEL_HEIGHT = 240.0, 160.0
PANELS_ACROSS = 3
ARROW_GAP = 40.0
ROW_GAP = 30.0
NUMBER_SIZE = 14.0
ARROW_LAYOUTS = frozenset({"sequence", "before_after"})
PANEL_BOXES: Mapping[int, tuple[tuple[float, float, float], ...]] = MappingProxyType(
    {
        1: ((50, 10, 140),),
        2: ((6, 22, 116), (118, 22, 116)),
        3: ((2, 10, 140), (150, 4, 76), (150, 80, 76)),
    }
)
PART_NODES: Mapping[str, Callable[[Any], list[Node]]] = MappingProxyType(
    {
        "cloth": cloth_nodes,
        "block": block_nodes,
        "bath": bath_nodes,
        "paste": paste_nodes,
        "heat": heat_nodes,
        "water": water_nodes,
        "tool": tool_nodes,
        "section": section_nodes,
        "piece": piece_nodes,
    }
)
SCENE_PARTS: TypeAdapter[list[KitPartSpec]] = TypeAdapter(list[KitPartSpec])


def part_still(part: KitPartSpec) -> Still:
    return svg_still(_svg(PART_BOX, PART_BOX, PART_NODES[part.part](part)))


def scene_still(parts: Sequence[KitPartSpec]) -> Still:
    return svg_still(_svg(PANEL_WIDTH, PANEL_HEIGHT, _placed_parts(parts)))


def kit_scene_parts(value: object) -> list[KitPartSpec] | None:
    if not isinstance(value, Mapping) or KIT_SCENE_MARK not in value:
        return None
    try:
        return SCENE_PARTS.validate_python(value[KIT_SCENE_MARK])
    except ValidationError:
        return None


def diagram_still(spec: DeclaredDiagramSpec) -> Still:
    if spec.layout == "section":
        return part_still(spec.panels[0].parts[0])
    count = len(spec.panels)
    across = min(PANELS_ACROSS, count)
    rows = math.ceil(count / across)
    width = across * PANEL_WIDTH + (across - 1) * ARROW_GAP
    height = rows * PANEL_HEIGHT + (rows - 1) * ROW_GAP
    pieces: list[tuple[Still, Affine]] = []
    for at, panel in enumerate(spec.panels):
        left, top = _cell(at, across)
        pieces.append((scene_still(panel.parts), translated(left, top)))
        pieces.append((_number(at + 1), translated(left, top)))
        if spec.layout in ARROW_LAYOUTS and at > 0 and at % across:
            pieces.append((_arrow(), translated(left - ARROW_GAP, top)))
    return merged(width, height, pieces)


def _cell(at: int, across: int) -> tuple[float, float]:
    column, row = at % across, at // across
    return column * (PANEL_WIDTH + ARROW_GAP), row * (PANEL_HEIGHT + ROW_GAP)


def _placed_parts(parts: Sequence[KitPartSpec]) -> list[Node]:
    boxes = PANEL_BOXES[min(len(parts), len(PANEL_BOXES))]
    return [
        group(PART_NODES[part.part](part), f"translate({x:g} {y:g}) scale({size / PART_BOX:.4f})")
        for part, (x, y, size) in zip(parts, boxes, strict=False)
    ]


def _number(number: int) -> Still:
    text = StillText(at=(4.0, NUMBER_SIZE), text=str(number), size=NUMBER_SIZE, colour=ink(1))
    return Still(width=PANEL_WIDTH, height=PANEL_HEIGHT, texts=(text,))


def _arrow() -> Still:
    middle = PANEL_HEIGHT / 2
    d = f"M6 {middle:g} H34 M27 {middle - 7:g} L34 {middle:g} L27 {middle + 7:g}"
    return svg_still(_svg(ARROW_GAP, PANEL_HEIGHT, [path(d, stroke=INK, width="2")]))


def _svg(width: float, height: float, children: list[Node]) -> Node:
    return {"tag": "svg", "attrs": {"viewBox": f"0 0 {width:g} {height:g}"}, "children": children}
