from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache

from app.research.map_layer_proposals import INDIA_FRAME

from .ground_frame import clip_line, clip_ring, framed, thinned
from .ground_layers import GroundLayers, decode_flagged, decode_records

__all__ = [
    "DISTRICT_LINES_SHARE",
    "SITE_HEIGHT",
    "SITE_WIDTH",
    "STEPS_ACROSS",
    "WHOLE_SITE",
    "BaseAsk",
    "BaseShapes",
    "BaseSources",
    "SiteBox",
    "base_shapes",
    "draws_district_lines",
    "named_points",
    "projected_frame",
    "site_degrees",
    "site_point",
]

SITE_WIDTH = 1000.0
SITE_PADDING = 24.0
DISTRICT_LINES_SHARE = 0.35
FRAME_ASPECT = 0.8
STEPS_ACROSS = 640
ACROSS = math.cos(math.radians((INDIA_FRAME.south + INDIA_FRAME.north) / 2))
UNITS_PER_DEGREE = (SITE_WIDTH - 2 * SITE_PADDING) / ((INDIA_FRAME.east - INDIA_FRAME.west) * ACROSS)
SITE_HEIGHT = (INDIA_FRAME.north - INDIA_FRAME.south) * UNITS_PER_DEGREE + 2 * SITE_PADDING
RING_POINTS = 3
RELIEF_FIRST_STEP = 2

Point = tuple[float, float]
Line = tuple[Point, ...]
Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class SiteBox:
    x: float
    y: float
    width: float
    height: float

    def degrees(self) -> Box:
        west, north = site_degrees(self.x, self.y)
        east, south = site_degrees(self.x + self.width, self.y + self.height)
        return west, south, east, north


WHOLE_SITE = SiteBox(0.0, 0.0, SITE_WIDTH, SITE_HEIGHT)


@dataclass(frozen=True)
class BaseSources:
    outline: str
    states: str
    districts: tuple[tuple[int, int, tuple[str, ...]], ...]


@dataclass(frozen=True)
class BaseAsk:
    relief: bool
    rivers: bool
    districts: bool
    homes: tuple[int, ...] = ()


@dataclass(frozen=True)
class BaseShapes:
    land: tuple[Line, ...]
    holes: tuple[Line, ...]
    coast: tuple[Line, ...]
    relief: tuple[tuple[int, tuple[Line, ...]], ...]
    lakes: tuple[Line, ...]
    rivers: tuple[tuple[int, Line], ...]
    districts: tuple[Line, ...]
    states: tuple[Line, ...]
    homes: tuple[Line, ...]


def site_point(longitude: float, latitude: float) -> Point:
    x = SITE_PADDING + (longitude - INDIA_FRAME.west) * ACROSS * UNITS_PER_DEGREE
    return x, SITE_PADDING + (INDIA_FRAME.north - latitude) * UNITS_PER_DEGREE


def site_degrees(x: float, y: float) -> Point:
    longitude = INDIA_FRAME.west + (x - SITE_PADDING) / (ACROSS * UNITS_PER_DEGREE)
    return longitude, INDIA_FRAME.north - (y - SITE_PADDING) / UNITS_PER_DEGREE


def draws_district_lines(box: SiteBox, asked: bool) -> bool:
    return asked or box.width <= SITE_WIDTH * DISTRICT_LINES_SHARE


def projected_frame(points: Sequence[Point], *, min_share: float, padding_share: float) -> SiteBox:
    if not points:
        return WHOLE_SITE
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    padded = max(max(xs) - min(xs), (max(ys) - min(ys)) / FRAME_ASPECT) * (1 + 2 * padding_share)
    width = min(SITE_WIDTH, max(padded, SITE_WIDTH * min_share))
    height = min(SITE_HEIGHT, width * FRAME_ASPECT)
    if width >= SITE_WIDTH:
        return WHOLE_SITE
    x = _clamped((max(xs) + min(xs)) / 2, width, SITE_WIDTH)
    y = _clamped((max(ys) + min(ys)) / 2, height, SITE_HEIGHT)
    return SiteBox(round(x, 1), round(y, 1), round(width, 1), round(height, 1))


def base_shapes(layers: GroundLayers, sources: BaseSources, box: SiteBox, ask: BaseAsk) -> BaseShapes:
    degrees = box.degrees()
    step = max(degrees[2] - degrees[0], degrees[3] - degrees[1]) / STEPS_ACROSS
    ground = framed(layers, degrees)
    land, holes = _outline(sources.outline)
    homes = [ring for lgd, rings in _districts(sources) if lgd in ask.homes for ring in rings]
    district_rings = [ring for _, rings in _districts(sources) for ring in rings]
    placed = _Placed(box, degrees, step)
    steps = {band.low_m: at for at, band in enumerate(layers.bands, start=RELIEF_FIRST_STEP)}
    return BaseShapes(
        land=placed.rings(land),
        holes=placed.rings(holes),
        coast=placed.lines(_closed([*land, *holes])),
        relief=tuple((steps[band.low_m], placed.cut(band.rings)) for band in ground.bands)
        if ask.relief
        else (),
        lakes=placed.cut(ground.lakes) if ask.rivers else (),
        rivers=tuple((line.rank, placed.line(line.points)) for line in ground.rivers) if ask.rivers else (),
        districts=placed.lines(_closed(district_rings)) if draws_district_lines(box, ask.districts) else (),
        states=placed.lines(_lines(sources.states)),
        homes=placed.lines(_closed(homes)),
    )


@dataclass(frozen=True)
class _Placed:
    box: SiteBox
    degrees: Box
    step: float

    def line(self, points: Sequence[Point]) -> Line:
        return tuple((x - self.box.x, y - self.box.y) for x, y in (site_point(*point) for point in points))

    def cut(self, rings: Sequence[Sequence[Point]]) -> tuple[Line, ...]:
        return tuple(self.line(ring) for ring in rings if len(ring) >= RING_POINTS)

    def rings(self, rings: Sequence[Sequence[Point]]) -> tuple[Line, ...]:
        kept = (thinned(clip_ring(ring, self.degrees), self.step, closed=True) for ring in rings)
        return self.cut([ring for ring in kept if ring])

    def lines(self, lines: Sequence[Sequence[Point]]) -> tuple[Line, ...]:
        runs = (run for line in lines for run in clip_line(line, self.degrees))
        kept = (thinned(run, self.step, closed=False) for run in runs)
        return tuple(self.line(run) for run in kept if run)


@cache
def _outline(payload: str) -> tuple[tuple[Line, ...], tuple[Line, ...]]:
    records = decode_flagged(payload)
    land = tuple(tuple(points) for hole, points in records if not hole)
    holes = tuple(tuple(points) for hole, points in records if hole)
    return land, holes


@cache
def _lines(payload: str) -> tuple[Line, ...]:
    return tuple(tuple(points) for points in decode_records(payload))


def named_points(sources: BaseSources, *, district: int | None, state: int | None) -> list[Point]:
    return [
        point
        for (lgd, rings), (_, owner, _) in zip(_districts(sources), sources.districts, strict=True)
        if lgd == district or owner == state
        for ring in rings
        for point in ring
    ]


@cache
def _districts(sources: BaseSources) -> tuple[tuple[int, tuple[Line, ...]], ...]:
    return tuple(
        (lgd, tuple(tuple(points) for encoded in rings for points in decode_records(encoded)))
        for lgd, _, rings in sources.districts
    )


def _closed(rings: Sequence[Line]) -> list[Line]:
    return [(*ring, ring[0]) for ring in rings if ring]


def _clamped(centre: float, size: float, span: float) -> float:
    return min(max(centre - size / 2, 0.0), span - size)
