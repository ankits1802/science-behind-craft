from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import shapely
from geo_etl.osm_rivers import RECORD_SEPARATOR, shown_name
from shapely.geometry import box, shape
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from .geo import lines_of
from .sources import BOUNDS

__all__ = [
    "DAM_REACH",
    "ENDPOINT_DIGITS",
    "POINT_DIGITS",
    "RIVER_KINDS",
    "TILE_DEGREES",
    "WATERS_TOLERANCE",
    "Dam",
    "DamSite",
    "Reservoir",
    "River",
    "WaterFeatures",
    "WaterWay",
    "cell_of",
    "named_dams",
    "osm_ref",
    "read_features",
    "river_parts",
    "rivers_of",
    "tile_bounds",
    "tile_id",
]

WATERS_TOLERANCE = 0.002
TILE_DEGREES = 2
POINT_DIGITS = 4
ENDPOINT_DIGITS = 7
DAM_REACH = 0.0005
RIVER_KINDS = frozenset({"river", "stream"})
RESERVOIR_TAGS = (("water", "reservoir"), ("landuse", "reservoir"))
AREAS = frozenset({"Polygon", "MultiPolygon"})
OSM_TYPES = {"n": "node", "w": "way", "r": "relation"}


@dataclass(frozen=True)
class WaterWay:
    way: int
    name: str
    kind: str
    line: BaseGeometry


@dataclass(frozen=True)
class DamSite:
    ref: str
    name: str | None
    geometry: BaseGeometry


@dataclass(frozen=True)
class Reservoir:
    ref: str
    name: str
    geometry: BaseGeometry


@dataclass
class WaterFeatures:
    ways: list[WaterWay] = field(default_factory=list)
    dams: list[DamSite] = field(default_factory=list)
    reservoirs: list[Reservoir] = field(default_factory=list)


@dataclass(frozen=True)
class River:
    id: int
    name: str
    kind: str
    lines: tuple[BaseGeometry, ...]


@dataclass(frozen=True)
class Dam:
    ref: str
    name: str
    named_by: str
    longitude: float
    latitude: float


def osm_ref(value: str) -> str | None:
    kind = OSM_TYPES.get(value[:1])
    return f"{kind}/{value[1:]}" if kind and value[1:].isdigit() else None


def read_features(path: Path) -> WaterFeatures:
    found = WaterFeatures()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip().lstrip(RECORD_SEPARATOR)
            if text:
                _sort(json.loads(text), found)
    return found


def _sort(feature: Mapping[str, Any], found: WaterFeatures) -> None:
    tags = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    ref = osm_ref(str(feature.get("id", "")))
    if not geometry or ref is None:
        return
    name = shown_name(tags)
    waterway = tags.get("waterway")
    if waterway in RIVER_KINDS and name and geometry.get("type") == "LineString" and ref.startswith("way/"):
        found.ways.append(WaterWay(int(ref.removeprefix("way/")), name, str(waterway), shape(geometry)))
    elif waterway == "dam":
        found.dams.append(DamSite(ref, name, shape(geometry)))
    elif (
        name
        and geometry.get("type") in AREAS
        and any(tags.get(key) == value for key, value in RESERVOIR_TAGS)
    ):
        found.reservoirs.append(Reservoir(ref, name, shape(geometry)))


def _ends(line: BaseGeometry) -> tuple[tuple[float, float], ...]:
    coords = list(line.coords)
    return tuple((round(x, ENDPOINT_DIGITS), round(y, ENDPOINT_DIGITS)) for x, y in (coords[0], coords[-1]))


def rivers_of(ways: Iterable[WaterWay]) -> list[River]:
    listed = list(ways)
    parent = list(range(len(listed)))

    def root(at: int) -> int:
        while parent[at] != at:
            parent[at] = parent[parent[at]]
            at = parent[at]
        return at

    met: dict[tuple[str, tuple[float, float]], int] = {}
    for at, way in enumerate(listed):
        for end in _ends(way.line):
            joined = met.setdefault((way.name, end), at)
            parent[root(at)] = root(joined)
    groups: dict[int, list[WaterWay]] = defaultdict(list)
    for at, way in enumerate(listed):
        groups[root(at)].append(way)
    return sorted((_river(group) for group in groups.values()), key=lambda river: river.id)


def _river(group: list[WaterWay]) -> River:
    ordered = sorted(group, key=lambda way: way.way)
    kind = "river" if any(way.kind == "river" for way in ordered) else "stream"
    return River(ordered[0].way, ordered[0].name, kind, tuple(way.line for way in ordered))


def named_dams(dams: Iterable[DamSite], reservoirs: list[Reservoir]) -> list[Dam]:
    tree = STRtree([reservoir.geometry for reservoir in reservoirs]) if reservoirs else None
    frame = box(*BOUNDS)
    named = []
    for dam in dams:
        name, named_by = _dam_name(dam, reservoirs, tree)
        point = _dam_point(dam.geometry)
        if name and frame.contains(point):
            named.append(
                Dam(dam.ref, name, named_by, round(point.x, POINT_DIGITS), round(point.y, POINT_DIGITS))
            )
    return sorted(named, key=lambda dam: (dam.name, dam.ref))


def _dam_name(dam: DamSite, reservoirs: list[Reservoir], tree: STRtree | None) -> tuple[str | None, str]:
    if dam.name:
        return dam.name, "dam"
    if tree is None:
        return None, ""
    reach = shapely.buffer(dam.geometry, DAM_REACH)
    held = {reservoirs[int(index)].name for index in tree.query(reach, predicate="intersects")}
    return (held.pop(), "reservoir") if len(held) == 1 else (None, "")


def _dam_point(geometry: BaseGeometry) -> BaseGeometry:
    lines = lines_of(geometry) if geometry.geom_type in ("LineString", "MultiLineString") else []
    if lines:
        longest = max(lines, key=lambda line: line.length)
        return longest.interpolate(0.5, normalized=True)
    return geometry if geometry.geom_type == "Point" else geometry.representative_point()


def cell_of(longitude: float, latitude: float) -> tuple[int, int]:
    return (
        math.floor(longitude / TILE_DEGREES) * TILE_DEGREES,
        math.floor(latitude / TILE_DEGREES) * TILE_DEGREES,
    )


def tile_id(west: int, south: int) -> str:
    return f"e{west:03d}n{south:02d}"


def tile_bounds(west: int, south: int) -> tuple[float, float, float, float]:
    frame_west, frame_south, frame_east, frame_north = BOUNDS
    return (
        max(float(west), frame_west),
        max(float(south), frame_south),
        min(float(west + TILE_DEGREES), frame_east),
        min(float(south + TILE_DEGREES), frame_north),
    )


def _cells(bounds: Iterable[float]) -> list[tuple[int, int]]:
    west, south, east, north = bounds
    low, bottom = cell_of(west, south)
    high, top = cell_of(east, north)
    cells = [
        (cell_west, cell_south)
        for cell_west in range(low, high + 1, TILE_DEGREES)
        for cell_south in range(bottom, top + 1, TILE_DEGREES)
    ]
    return [cell for cell in cells if _held(tile_bounds(*cell))]


def _held(bounds: tuple[float, float, float, float]) -> bool:
    west, south, east, north = bounds
    return west < east and south < north


def river_parts(river: River, tolerance: float) -> dict[tuple[int, int], list[list[tuple[float, float]]]]:
    simplified = [shapely.simplify(line, tolerance) for line in river.lines]
    parts: dict[tuple[int, int], list[list[tuple[float, float]]]] = {}
    for cell in _cells(shapely.total_bounds(simplified)):
        cut = box(*tile_bounds(*cell))
        kept = [
            list(part.coords) for line in simplified for part in lines_of(shapely.intersection(line, cut))
        ]
        if kept:
            parts[cell] = kept
    return parts
