from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.research.component_specs_kit import HeatPart, ToolPart, WaterPart

from .export_still_kit_surfaces import (
    INK,
    INK_FAINT,
    INK_SOFT,
    NEUTRAL_LIQUOR,
    PAPER,
    SHADE,
    WELL,
    Node,
    group,
    line_path,
    material_path,
    path,
    rect_d,
)

__all__ = ["heat_nodes", "tool_nodes", "water_nodes"]

FLAME = "M60 34 C68 46 78 52 76 68 C75 80 68 88 60 88 C52 88 45 80 44 68 C43 56 54 50 60 34 Z"
SIDE_FLAMES = (
    "M42 56 C47 64 50 70 48 80 C46 86 40 88 36 84 C32 78 34 68 42 56 Z",
    "M78 56 C86 68 88 78 84 84 C80 88 74 86 72 80 C70 70 73 64 78 56 Z",
)
INNER = "M60 58 C64 64 67 70 65 76 C64 80 62 82 60 82 C58 82 56 80 55 76 C54 70 56 64 60 58 Z"
LOGS = ("M26 92 L94 104 L92 112 L24 100 Z", "M26 104 L94 92 L96 100 L28 112 Z")
DOME = "M12 108 C12 62 34 34 60 34 C86 34 108 62 108 108 Z"
MOUTH = "M42 108 C42 86 78 86 78 108 Z"
DIYA = "M24 84 C30 102 90 102 96 84 C80 90 40 90 24 84 Z"
DROP = "M0 -9 C3 -4 5 -1 5 2 C5 5 3 7 0 7 C-3 7 -5 5 -5 2 C-5 -1 -3 -4 0 -9 Z"
DROPS = ((30, 26), (58, 18), (86, 30), (44, 52), (74, 56))
FIST = "M-13 -8 C-13 -12 -9 -14 -5 -14 H7 C11 -14 14 -11 14 -7 V6 C14 10 11 12 7 12 H-6 C-10 12 -13 9 -13 5 Z"
THUMB = "M-13 -2 C-19 -2 -21 5 -16 8 C-13 10 -9 9 -8 5"
KNUCKLES = "M-4 -14 V-7 M2 -14 V-7 M8 -13 V-7"


@dataclass(frozen=True)
class Drawn:
    body: tuple[str, ...]
    grip: float
    tip: str | None = None
    steel: str | None = None


AXIS_TOOLS: Mapping[str, Drawn] = MappingProxyType(
    {
        "brush": Drawn(
            ("M-42 -3 H8 V3 H-42 Z", "M8 -4 H18 V4 H8 Z"),
            -14,
            tip="M18 -4.5 C30 -4.5 38 -1.5 44 0 C38 1.5 30 4.5 18 4.5 Z",
        ),
        "chisel": Drawn(
            ("M-36 -6 C-38 -6 -40 -4 -40 0 C-40 4 -38 6 -36 6 H4 V-6 Z",),
            -18,
            steel="M4 -3 H34 L44 0 L34 3 H4 Z",
        ),
        "mallet": Drawn(
            (
                "M-42 -3 H14 V3 H-42 Z",
                "M14 -15 C14 -17 15 -18 17 -18 H37 C39 -18 40 -17 40 -15 V15 C40 17 39 18 37 18 H17 C15 18 14 17 14 15 Z",
            ),
            -20,
        ),
        "knife": Drawn(
            ("M-34 -5 C-36 -5 -37 -3 -37 0 C-37 3 -36 5 -34 5 H4 V-5 Z",),
            -16,
            steel="M4 -4 H38 C42 -4 45 -1 45 1 L4 4 Z",
        ),
        "stick": Drawn(
            ("M-42 -4 C-44 -4 -45 -2 -45 0 C-45 2 -44 4 -42 4 H42 C44 4 45 2 45 0 C45 -2 44 -4 42 -4 Z",), -22
        ),
    }
)


def heat_nodes(part: HeatPart) -> list[Node]:
    if part.source == "sun":
        return _sun()
    if part.source == "fire":
        return [*_flames(1.0), *(node for d in LOGS for node in line_path(d))]
    if part.source == "furnace":
        smoke = "M40 30 q4 -6 0 -12 M60 26 q4 -6 0 -12 M80 30 q4 -6 0 -12"
        return [
            *line_path(DOME),
            path(MOUTH, fill=WELL, stroke=INK, width="1.2"),
            *_flames(0.34),
            path("M104 96 L118 82", stroke=INK, width="3"),
            path(smoke, stroke=INK_FAINT, width="1.2"),
        ]
    lamp = group([*line_path(FLAME), path(INNER, stroke=INK_SOFT, width="1.6")], "translate(66 30) scale(.5)")
    return [*line_path(DIYA), path("M86 86 L100 80", stroke=INK, width="2"), lamp]


def _sun() -> list[Node]:
    rays: list[str] = []
    for at in range(12):
        cos, sin = math.cos(math.pi * at / 6), math.sin(math.pi * at / 6)
        rays.append(f"M{60 + 30 * cos:.1f} {60 + 30 * sin:.1f} L{60 + 42 * cos:.1f} {60 + 42 * sin:.1f}")
    disc = {"cx": "60", "cy": "60"}
    return [
        {"tag": "circle", "attrs": {**disc, "r": "22", "fill": PAPER, "stroke": INK, "stroke-width": "1.4"}},
        {
            "tag": "circle",
            "attrs": {**disc, "r": "15", "fill": "none", "stroke": INK_FAINT, "stroke-width": ".9"},
        },
        path(" ".join(rays), stroke=INK, width="1.6"),
    ]


def _flames(scale: float) -> list[Node]:
    nodes = [*(node for d in SIDE_FLAMES for node in line_path(d)), *line_path(FLAME)]
    nodes.append(path(INNER, stroke=INK_SOFT, width="1.1"))
    if scale == 1.0:
        return nodes
    return [group(nodes, f"translate({60 - 60 * scale:.2f} {88 - 88 * scale:.2f}) scale({scale})")]


def water_nodes(part: WaterPart) -> list[Node]:
    if part.form == "running":
        waves = " ".join(_wave(y) for y in (42, 62, 82))
        return [
            path(rect_d(2, 20, 116, 82), fill=NEUTRAL_LIQUOR),
            path("M2 20 H118 M2 102 H118", stroke=INK, width="1.4"),
            path(waves, stroke=INK_SOFT, width="1.6"),
            path("M100 30 L112 30 M106 25 L112 30 L106 35", stroke=INK, width="1.6"),
        ]
    if part.form == "still":
        rings = [_ellipse(rx, ry, "none", INK_SOFT, "1") for rx, ry in ((34, 18), (22, 12), (10, 6))]
        return [_ellipse(54, 30, NEUTRAL_LIQUOR, INK, "1.4"), *rings]
    drops = [
        group([path(DROP, fill=NEUTRAL_LIQUOR, stroke=INK_SOFT, width="1.2")], f"translate({x} {y})")
        for x, y in DROPS
    ]
    return [
        path("M10 96 H110", stroke=INK, width="1.6"),
        path("M22 104 H98", stroke=INK_FAINT, width="1"),
        *drops,
        path("M40 92 q4 -4 8 0 M70 92 q4 -4 8 0", stroke=INK_SOFT, width="1.2"),
    ]


def _wave(y: float) -> str:
    return f"M6 {y:g} C18 {y - 7:g} 30 {y + 7:g} 42 {y:g} S66 {y - 7:g} 78 {y:g} S102 {y + 7:g} 110 {y:g}"


def _ellipse(rx: float, ry: float, fill: str, stroke: str, width: str) -> Node:
    return {
        "tag": "ellipse",
        "attrs": {
            "cx": "60",
            "cy": "66",
            "rx": f"{rx:g}",
            "ry": f"{ry:g}",
            "fill": fill,
            "stroke": stroke,
            "stroke-width": width,
        },
    }


def tool_nodes(part: ToolPart) -> list[Node]:
    if part.tool == "block":
        return _block_in_hand(part)
    drawn = AXIS_TOOLS[part.tool]
    nodes: list[Node] = []
    for d in drawn.body:
        nodes += _loaded(d, part.load if part.tool == "stick" else None)
    if drawn.steel:
        nodes += line_path(drawn.steel, fill=SHADE)
    if drawn.tip:
        nodes += _loaded(drawn.tip, part.load)
    if part.held:
        nodes.append(_fist(drawn.grip, 0))
    return [group(nodes, "translate(60 62) rotate(-32)")]


def _block_in_hand(part: ToolPart) -> list[Node]:
    nodes = [
        *line_path("M22 74 H90 V100 H22 Z", fill=SHADE),
        *line_path("M90 74 L104 62 V88 L90 100 Z", fill=SHADE),
        *line_path("M22 74 L36 62 H104 L90 74 Z"),
    ]
    if part.load:
        nodes += material_path("M22 100 H90 V104 H22 Z", part.load)
    else:
        nodes.append(path("M22 100 H90", stroke=INK, width="2.2"))
    nodes += line_path("M54 66 C54 56 58 48 63 48 C68 48 72 56 72 66 Z")
    if part.held:
        nodes.append(_fist(63, 42))
    return nodes


def _loaded(d: str, load: str | None) -> list[Node]:
    return material_path(d, load) if load else line_path(d)


def _fist(x: float, y: float) -> Node:
    return group(
        [
            *line_path(FIST),
            path(KNUCKLES, stroke=INK_SOFT, width="1"),
            path(THUMB, fill=PAPER, stroke=INK, width="1.2"),
        ],
        f"translate({x:g} {y:g})",
    )
