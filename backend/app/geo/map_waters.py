from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from .ground_frame import clip_line, thinned
from .ground_layers import decode_records
from .map_base import STEPS_ACROSS, SiteBox, draws_district_lines, site_point

__all__ = [
    "NO_WATERS",
    "NamedDam",
    "NamedRiver",
    "WaterAsk",
    "WaterShapes",
    "WaterTile",
    "shows_waters",
    "tiles_in_box",
    "water_shapes",
    "water_tile",
]

Point = tuple[float, float]
Line = tuple[Point, ...]
Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class WaterAsk:
    rivers: tuple[str, ...] = ()
    dams: tuple[str, ...] = ()
    plain: bool = True


@dataclass(frozen=True)
class WaterTile:
    rivers: tuple[tuple[tuple[str, ...], tuple[Line, ...]], ...]
    dams: tuple[tuple[str, Point], ...]
    plain: tuple[Line, ...]


@dataclass(frozen=True)
class NamedRiver:
    name: str
    lines: tuple[Line, ...]
    at: Point


@dataclass(frozen=True)
class NamedDam:
    name: str
    at: Point


@dataclass(frozen=True)
class WaterShapes:
    lines: tuple[Line, ...] = ()
    strong: tuple[NamedRiver, ...] = ()
    dams: tuple[NamedDam, ...] = ()

    @property
    def drawn(self) -> bool:
        return bool(self.lines or self.strong or self.dams)


NO_WATERS = WaterShapes()


def shows_waters(box: SiteBox) -> bool:
    return draws_district_lines(box, False)


def water_tile(body: Mapping[str, Any]) -> WaterTile:
    rivers = tuple(
        ((str(row["name"]), *(str(name) for name in row.get("also", ()))), _decoded(str(row["lines"])))
        for row in body["rivers"]
    )
    dams = tuple(
        (str(row["name"]), (float(row["longitude"]), float(row["latitude"]))) for row in body["dams"]
    )
    return WaterTile(rivers=rivers, dams=dams, plain=_decoded(str(body.get("plain") or "")))


def tiles_in_box(rows: Sequence[Mapping[str, Any]], box: SiteBox) -> list[str]:
    if not shows_waters(box):
        return []
    return [str(row["id"]) for row in rows if _overlaps(_tile_box(row["bounds"]), box)]


def water_shapes(tiles: Sequence[WaterTile], box: SiteBox, ask: WaterAsk) -> WaterShapes:
    if not shows_waters(box):
        return NO_WATERS
    cut = _Cut.of(box)
    rivers = [river for tile in tiles for river in tile.rivers]
    every = [line for _, lines in rivers for line in lines] + [line for tile in tiles for line in tile.plain]
    dams = tuple(
        NamedDam(name, cut.point(at))
        for tile in tiles
        for name, at in tile.dams
        if name in ask.dams and cut.holds(at)
    )
    return WaterShapes(
        lines=cut.lines(every) if ask.plain else (),
        strong=tuple(found for name in ask.rivers for found in _strong(cut, rivers, name)),
        dams=dams,
    )


@dataclass(frozen=True)
class _Cut:
    box: SiteBox
    degrees: Box
    step: float

    @classmethod
    def of(cls, box: SiteBox) -> _Cut:
        degrees = box.degrees()
        return cls(box, degrees, max(degrees[2] - degrees[0], degrees[3] - degrees[1]) / STEPS_ACROSS)

    def point(self, at: Point) -> Point:
        x, y = site_point(*at)
        return x - self.box.x, y - self.box.y

    def holds(self, at: Point) -> bool:
        west, south, east, north = self.degrees
        return west <= at[0] <= east and south <= at[1] <= north

    def lines(self, lines: Sequence[Line]) -> tuple[Line, ...]:
        runs = (run for line in lines for run in clip_line(line, self.degrees))
        kept = (thinned(run, self.step, closed=False) for run in runs)
        return tuple(tuple(self.point(point) for point in run) for run in kept if len(run) >= 2)


def _strong(
    cut: _Cut, rivers: Sequence[tuple[tuple[str, ...], tuple[Line, ...]]], name: str
) -> list[NamedRiver]:
    lines = cut.lines([line for names, found in rivers if name in names for line in found])
    if not lines:
        return []
    return [NamedRiver(name=name, lines=lines, at=_midway(max(lines, key=_length)))]


def _length(line: Line) -> float:
    return sum(math.dist(a, b) for a, b in pairwise(line))


def _midway(line: Line) -> Point:
    left = _length(line) / 2
    for a, b in pairwise(line):
        step = math.dist(a, b)
        if step >= left and step > 0:
            share = left / step
            return a[0] + (b[0] - a[0]) * share, a[1] + (b[1] - a[1]) * share
        left -= step
    return line[0]


def _tile_box(bounds: Sequence[float]) -> SiteBox:
    west, south, east, north = (float(value) for value in bounds)
    corner, far = site_point(west, north), site_point(east, south)
    return SiteBox(corner[0], corner[1], far[0] - corner[0], far[1] - corner[1])


def _overlaps(one: SiteBox, other: SiteBox) -> bool:
    return (
        one.x < other.x + other.width
        and other.x < one.x + one.width
        and one.y < other.y + other.height
        and other.y < one.y + one.height
    )


def _decoded(payload: str) -> tuple[Line, ...]:
    return tuple(tuple(points) for points in decode_records(payload)) if payload else ()
