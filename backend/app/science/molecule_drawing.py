from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from app.research.component_specs_science_geometry import (
    ATOM_MARK,
    BOND_MARK,
    MOLECULE_GROUP,
    MoleculeGeometry,
)
from app.research.drawing_rules import text_floor

from .molecule_elements import ELEMENTS, atom_token

__all__ = [
    "ATOM_RADII",
    "GRADIENT_PREFIX",
    "LETTERED",
    "REST_PITCH",
    "REST_YAW",
    "VIEW_WIDTH",
    "atom_gradient",
    "molecule_drawing",
]

ATOM_RADII = MappingProxyType({symbol: element.radius for symbol, element in ELEMENTS.items()})
LETTERED = frozenset(symbol for symbol, element in ELEMENTS.items() if element.lettered)
REST_YAW = 0.4
REST_PITCH = 0.3
VIEW_WIDTH = 2.0
VIEW_BOX = "-1 -1 2 2"
FILL_SHARE = 0.95
DEPTH_SWELL = 0.14
BOND_WIDTH = 0.11
DOUBLE_WIDTH = 0.7
DOUBLE_OFFSET = 0.07
BOND_BEHIND = 0.08
LETTER_SCALE = 1.15
LETTER_HIDDEN = 2.3
LETTER_FLOOR = text_floor(VIEW_WIDTH)
EDGE_WIDTH = "0.005"
PLACES = 1000
DOUBLE = 2
GRADIENT_PREFIX = "ag-"
GRADIENT = (
    '<radialGradient id="{id}" cx=".36" cy=".32" r=".72">'
    '<stop offset="0" style="stop-color:color-mix(in srgb, var({token}) 42%, #ffffff)"/>'
    '<stop offset=".6" style="stop-color:var({token})"/>'
    '<stop offset="1" style="stop-color:color-mix(in srgb, var({token}) 78%, #000000)"/>'
    "</radialGradient>"
)

Node = dict[str, Any]


@dataclass(frozen=True)
class _Point:
    symbol: str
    x: float
    y: float
    depth: float


def molecule_drawing(geometry: MoleculeGeometry, *, yaw: float, pitch: float) -> Node:
    scale = FILL_SHARE / geometry.radius
    points = [_turned(atom, yaw, pitch) for atom in geometry.atoms]
    placed = [(point.depth, _atom(index, point, scale)) for index, point in enumerate(points)]
    for index, (first, second, order) in enumerate(geometry.bonds):
        near, far = points[first], points[second]
        depth = (near.depth + far.depth) / 2 - BOND_BEHIND
        placed.append((depth, _bond(index, (near, far), order, scale)))
    nodes = [node for _, node in sorted(placed, key=lambda item: item[0])]
    group = {"tag": "g", "attrs": {"class": MOLECULE_GROUP}, "children": nodes}
    attrs = {"viewBox": VIEW_BOX, "aria-hidden": "true", "focusable": "false"}
    return {"tag": "svg", "attrs": attrs, "children": [group]}


def atom_gradient(symbol: str) -> str:
    return GRADIENT.format(id=f"{GRADIENT_PREFIX}{symbol}", token=atom_token(symbol))


def _turned(atom: tuple[str, float, float, float], yaw: float, pitch: float) -> _Point:
    symbol, x, y, z = atom
    turned_x = math.cos(yaw) * x + math.sin(yaw) * z
    turned_z = -math.sin(yaw) * x + math.cos(yaw) * z
    return _Point(
        symbol,
        turned_x,
        math.cos(pitch) * y - math.sin(pitch) * turned_z,
        math.sin(pitch) * y + math.cos(pitch) * turned_z,
    )


def _atom(index: int, point: _Point, scale: float) -> Node:
    radius = ATOM_RADII.get(point.symbol, ATOM_RADII["N"]) * scale * (1 + point.depth * scale * DEPTH_SWELL)
    x, y = _shown(point.x * scale), _shown(-point.y * scale)
    circle = {
        "tag": "circle",
        "attrs": {
            "cx": x,
            "cy": y,
            "r": _shown(radius),
            "fill": f"url(#{GRADIENT_PREFIX}{point.symbol})",
            "stroke": "var(--mol-edge)",
            "stroke-width": EDGE_WIDTH,
        },
    }
    children: list[Node] = [circle]
    size = max(radius * LETTER_SCALE, LETTER_FLOOR)
    if point.symbol in LETTERED and size <= radius * LETTER_HIDDEN:
        children.append(_letter(point.symbol, (x, y), size))
    return {"tag": "g", "attrs": {ATOM_MARK: str(index)}, "children": children}


def _letter(symbol: str, at: tuple[str, str], size: float) -> Node:
    attrs = {
        "x": at[0],
        "y": at[1],
        "font-size": _shown(size),
        "text-anchor": "middle",
        "dominant-baseline": "central",
        "fill": "var(--mol-letter)",
    }
    return {"tag": "text", "attrs": attrs, "children": [symbol]}


def _bond(index: int, ends: tuple[_Point, _Point], order: int, scale: float) -> Node:
    near, far = ends
    x1, y1, x2, y2 = near.x * scale, -near.y * scale, far.x * scale, -far.y * scale
    width = BOND_WIDTH * scale
    if order == DOUBLE:
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx * dx + dy * dy) or 1.0
        ox, oy = -dy / length * DOUBLE_OFFSET * scale, dx / length * DOUBLE_OFFSET * scale
        path = _line(x1 + ox, y1 + oy, x2 + ox, y2 + oy) + _line(x1 - ox, y1 - oy, x2 - ox, y2 - oy)
        width *= DOUBLE_WIDTH
    else:
        path = _line(x1, y1, x2, y2)
    attrs = {
        BOND_MARK: str(index),
        "d": path,
        "stroke": "var(--mol-bond)",
        "stroke-width": _shown(width),
        "stroke-linecap": "round",
    }
    return {"tag": "path", "attrs": attrs}


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f"M{_shown(x1)} {_shown(y1)}L{_shown(x2)} {_shown(y2)}"


def _shown(value: float) -> str:
    rounded = math.floor(value * PLACES + 0.5) / PLACES
    return str(int(rounded)) if rounded == int(rounded) else repr(rounded)
