from __future__ import annotations

import math
from typing import Any

__all__ = [
    "INK",
    "INK_FAINT",
    "INK_SOFT",
    "NEUTRAL_LIQUOR",
    "PAPER",
    "SHADE",
    "WELL",
    "Node",
    "PrintBox",
    "group",
    "line_path",
    "material_path",
    "motif_tiles",
    "paint",
    "path",
    "rect_d",
    "shaded",
    "star_points",
]

INK = "var(--ink-1)"
INK_SOFT = "var(--ink-2)"
INK_FAINT = "var(--ink-3)"
PAPER = "var(--raised)"
WELL = "var(--sunk)"
SHADE = "color-mix(in srgb, var(--ink-3) 22%, var(--raised))"
NEUTRAL_LIQUOR = "color-mix(in srgb, var(--ink-3) 18%, var(--sunk))"
TILE = 24.0
EDGE_WIDTH = "1.2"
STAR_POINTS = 16

Node = dict[str, Any]
PrintBox = tuple[float, float, float, float]


def paint(token: str) -> str:
    return f"var({token})"


def shaded(token: str, share: int) -> str:
    return f"color-mix(in srgb, {paint(token)} {share}%, black)"


def rect_d(x: float, y: float, width: float, height: float) -> str:
    return f"M{x:g} {y:g} H{x + width:g} V{y + height:g} H{x:g} Z"


def path(d: str, *, fill: str = "none", stroke: str | None = None, width: str | None = None) -> Node:
    attrs = {"d": d, "fill": fill}
    if stroke is not None:
        attrs["stroke"] = stroke
        attrs["stroke-width"] = width or "1"
    return {"tag": "path", "attrs": attrs}


def group(children: list[Node], transform: str | None = None, **attrs: str) -> Node:
    held = {**attrs, **({"transform": transform} if transform else {})}
    return {"tag": "g", "attrs": held, "children": children}


def material_path(
    d: str, material: str, *, edge: str | None = INK, tiles: list[Node] | None = None
) -> list[Node]:
    edged = [path(d, stroke=edge, width=EDGE_WIDTH)] if edge else []
    return [path(d, fill=paint(material)), *(tiles or []), *edged]


def line_path(d: str, *, fill: str = PAPER) -> list[Node]:
    return [path(d, fill=fill), path(d, stroke=INK, width=EDGE_WIDTH)]


def star_points(cx: float, cy: float, outer: float, inner: float) -> str:
    points = []
    for at in range(STAR_POINTS):
        radius = outer if at % 2 == 0 else inner
        angle = math.pi * at / 8 - math.pi / 2
        points.append(f"{cx + radius * math.cos(angle):.2f},{cy + radius * math.sin(angle):.2f}")
    return " ".join(points)


def motif_tiles(motif: str, box: PrintBox, material: str, size: float) -> list[Node]:
    x, y, width, height = box
    across, down = int(width // size), int(height // size)
    left, top = x + (width - across * size) / 2, y + (height - down * size) / 2
    tile = _tile(motif, paint(material))
    scale = size / TILE
    return [
        group(tile, f"translate({left + column * size:.2f} {top + row * size:.2f}) scale({scale:.4f})")
        for row in range(down)
        for column in range(across)
    ]


def _tile(motif: str, colour: str) -> list[Node]:
    if motif == "star":
        corners = [(0, 0), (24, 24), (24, 0), (0, 24)]
        return [
            path("M0 12 L12 0 L24 12 L12 24 Z", stroke=colour, width="1"),
            {"tag": "polygon", "attrs": {"points": star_points(12, 12, 7.5, 3.2), "fill": colour}},
            *(
                {"tag": "circle", "attrs": {"cx": f"{cx}", "cy": f"{cy}", "r": "1.6", "fill": colour}}
                for cx, cy in corners
            ),
        ]
    if motif == "lattice":
        return [path("M0 0 L24 24 M24 0 L0 24", stroke=colour, width="1.6")]
    if motif == "dots":
        return [
            {"tag": "circle", "attrs": {"cx": f"{cx}", "cy": f"{cx}", "r": "2.4", "fill": colour}}
            for cx in (6, 18)
        ]
    return [path("M0 6 H24 M0 18 H24", stroke=colour, width="2")]
