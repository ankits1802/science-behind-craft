from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .export_pdf_maps import MapProjection, district_outlines, map_projection
from .export_stills import WHITE, Point, Still, StillPath, StillText, ellipse_points, ink, token_colour

__all__ = ["MAP_HEIGHT", "MAP_WIDTH", "MapPin", "timeline_still"]

MAP_WIDTH = 300.0
MAP_HEIGHT = 240.0
PIN_RADIUS = 4.0
NUMBER_SIZE = 10.0
LONE_MARGIN = 1.0
LAND = "--sunk"
BORDER = "--rule"
HOME = "--terracotta"


@dataclass(frozen=True)
class MapPin:
    longitude: float
    latitude: float
    number: int


@dataclass(frozen=True)
class MapAsk:
    pins: Sequence[MapPin]
    routes: Sequence[tuple[int, int]]
    districts: Sequence[int]
    homes: Sequence[int]


def timeline_still(ask: MapAsk) -> Still:
    outlines = district_outlines(list(dict.fromkeys([*ask.districts, *ask.homes])))
    homes = set(ask.homes)
    points: list[Point] = [*outlines.points(), *((pin.longitude, pin.latitude) for pin in ask.pins)]
    projection = _framed(points)
    if projection is None:
        return Still(width=MAP_WIDTH, height=MAP_HEIGHT)
    land, border, home = _colour(LAND), _colour(BORDER), _colour(HOME)
    paths = [
        StillPath(points=tuple(projection.place(point) for point in ring), fill=land, line=border, width=0.6)
        for shape in outlines.context
        for ring in shape.rings
    ]
    paths += [
        StillPath(points=tuple(projection.place(point) for point in ring), fill=home, line=home, width=0.6)
        for shape in outlines.filled
        if shape.lgd in homes
        for ring in shape.rings
    ]
    placed = [projection.place((pin.longitude, pin.latitude)) for pin in ask.pins]
    paths += [
        StillPath(points=(placed[start], placed[end]), closed=False, line=ink(2), width=1.4)
        for start, end in ask.routes
        if start < len(placed) and end < len(placed)
    ]
    paths += [
        StillPath(points=ellipse_points(*at, PIN_RADIUS, PIN_RADIUS), fill=ink(1), line=WHITE)
        for at in placed
    ]
    texts = [
        StillText(
            at=(x + PIN_RADIUS + 2, y + NUMBER_SIZE / 3),
            text=str(pin.number),
            size=NUMBER_SIZE,
            colour=ink(1),
        )
        for pin, (x, y) in zip(ask.pins, placed, strict=True)
    ]
    return Still(width=projection.width, height=projection.height, paths=tuple(paths), texts=tuple(texts))


def _framed(points: Sequence[Point]) -> MapProjection | None:
    projection = map_projection(points, MAP_WIDTH, MAP_HEIGHT)
    if projection is not None or not points:
        return projection
    lon, lat = points[0]
    framed = [(lon - LONE_MARGIN, lat - LONE_MARGIN), (lon + LONE_MARGIN, lat + LONE_MARGIN)]
    return map_projection([*points, *framed], MAP_WIDTH, MAP_HEIGHT)


def _colour(token: str) -> tuple[int, int, int]:
    return token_colour(token) or ink(3)
