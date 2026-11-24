from __future__ import annotations

import math
from collections.abc import Sequence

from app.research.component_specs_science_geometry import MoleculeGeometry

from .export_stills import (
    Point,
    Still,
    StillPath,
    StillText,
    ellipse_points,
    ink,
    rect_points,
    token_colour,
)

__all__ = ["ATOM_PREFIX", "DIP_SWATCH", "molecule_still", "swatch_strip", "turned_atoms"]

ATOM_PREFIX = "--atom-"
MOLECULE_BOX = 240.0
MOLECULE_MARGIN = 16.0
ATOM_RADIUS = 0.34
HYDROGEN_RADIUS = 0.22
HYDROGEN = "H"
BOND_WIDTH = 1.6
DIP_SWATCH = 40.0
SWATCH_GAP = 10.0
NUMBER_SIZE = 11.0


def turned_atoms(geometry: MoleculeGeometry, yaw: float, pitch: float) -> list[tuple[float, float, float]]:
    turn, tilt = math.radians(yaw), math.radians(pitch)
    cos_y, sin_y, cos_p, sin_p = math.cos(turn), math.sin(turn), math.cos(tilt), math.sin(tilt)
    turned: list[tuple[float, float, float]] = []
    for _, x, y, z in geometry.atoms:
        x1, z1 = cos_y * x + sin_y * z, -sin_y * x + cos_y * z
        y1, z2 = cos_p * y - sin_p * z1, sin_p * y + cos_p * z1
        turned.append((x1, -y1, z2))
    return turned


def molecule_still(geometry: MoleculeGeometry, yaw: float, pitch: float) -> Still:
    turned = turned_atoms(geometry, yaw, pitch)
    xs, ys = [x for x, _, _ in turned], [y for _, y, _ in turned]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0) + 2 * ATOM_RADIUS
    scale = (MOLECULE_BOX - 2 * MOLECULE_MARGIN) / span
    middle = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)

    def at(index: int) -> Point:
        x, y, _ = turned[index]
        return MOLECULE_BOX / 2 + (x - middle[0]) * scale, MOLECULE_BOX / 2 + (y - middle[1]) * scale

    bonds = [
        StillPath(points=(at(first), at(second)), closed=False, line=ink(2), width=BOND_WIDTH * order)
        for first, second, order in geometry.bonds
    ]
    order = sorted(range(len(turned)), key=lambda index: turned[index][2])
    atoms = [_atom(geometry.atoms[index][0], at(index), scale) for index in order]
    return Still(width=MOLECULE_BOX, height=MOLECULE_BOX, paths=(*bonds, *atoms))


def _atom(symbol: str, centre: Point, scale: float) -> StillPath:
    radius = (HYDROGEN_RADIUS if symbol == HYDROGEN else ATOM_RADIUS) * scale
    colour = token_colour(f"{ATOM_PREFIX}{symbol.lower()}") or ink(3)
    return StillPath(points=ellipse_points(*centre, radius, radius), fill=colour, line=ink(1), width=0.8)


def swatch_strip(tokens: Sequence[str | None]) -> Still:
    paths: list[StillPath] = []
    texts: list[StillText] = []
    for at, token in enumerate(tokens):
        left = at * (DIP_SWATCH + SWATCH_GAP)
        colour = token_colour(token) if token else None
        box = rect_points(left, 0, DIP_SWATCH, DIP_SWATCH)
        paths.append(StillPath(points=box, fill=colour, line=ink(1), width=1.0))
        texts.append(
            StillText(
                at=(left + DIP_SWATCH / 2, DIP_SWATCH + NUMBER_SIZE + 2),
                text=str(at + 1),
                size=NUMBER_SIZE,
                colour=ink(2),
                anchor="middle",
            )
        )
    width = max(len(tokens), 1) * (DIP_SWATCH + SWATCH_GAP) - SWATCH_GAP
    return Still(width=width, height=DIP_SWATCH + NUMBER_SIZE + 4, paths=tuple(paths), texts=tuple(texts))
