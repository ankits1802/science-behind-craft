from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from shapely.geometry import MultiLineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from basemap.polyline import encode_records

from .sources import BOUNDS
from .waters import (
    TILE_DEGREES,
    WATERS_TOLERANCE,
    Dam,
    River,
    WaterFeatures,
    cell_of,
    named_dams,
    river_parts,
    rivers_of,
    tile_bounds,
    tile_id,
)
from .waters_names import WATERS_SCHEMA_VERSION, held_names, register_names
from .waters_register import Register

__all__ = [
    "TILES_MODULE",
    "WATERS_LICENCE",
    "WATERS_SCHEMA_VERSION",
    "WATERS_SITE",
    "WATERS_SOURCE",
    "WatersBuild",
    "district_finder",
    "tiles_module",
    "waters_build",
]

WATERS_SOURCE = "OpenStreetMap rivers, streams and dams, India extract by Geofabrik"
WATERS_SITE = "https://www.openstreetmap.org/copyright"
WATERS_LICENCE = "ODbL 1.0"
TILES_MODULE = (
    'import type {{ WatersTile }} from "@/lib/mapWaters";\n\n'
    "export const WATERS_TILES: Readonly<Record<string, () => Promise<WatersTile>>> = {{\n{rows}}};\n"
)
TILE_ROW = '  {tile}: () => import("@/public/layers/waters/{tile}.json").then((tile) => tile.default),\n'

Districts = Callable[[BaseGeometry], list[int]]


@dataclass(frozen=True)
class WatersBuild:
    index: dict[str, Any]
    tiles: dict[str, dict[str, Any]]
    names: dict[str, Any]


def district_finder(polygons: list[tuple[BaseGeometry, int, int]]) -> Districts:
    tree = STRtree([shape for shape, _, _ in polygons])
    codes = [lgd for _, lgd, _ in polygons]

    def found(geometry: BaseGeometry) -> list[int]:
        return sorted({codes[int(index)] for index in tree.query(geometry, predicate="intersects")})

    return found


def _river_row(river: River, register: Register, districts: Districts) -> dict[str, Any]:
    crossed = districts(MultiLineString(list(river.lines)))
    row: dict[str, Any] = {"id": river.id, "name": river.name, "kind": river.kind, "districts": crossed}
    return row | register_names(river.name, crossed, register)


def _dam_row(dam: Dam, districts: Districts) -> dict[str, Any]:
    point = Point(dam.longitude, dam.latitude)
    return {
        "ref": dam.ref,
        "name": dam.name,
        "namedBy": dam.named_by,
        "longitude": dam.longitude,
        "latitude": dam.latitude,
        "districts": districts(point),
    }


def _tile(tiles: dict[str, dict[str, Any]], cell: tuple[int, int]) -> dict[str, Any]:
    key = tile_id(*cell)
    if key not in tiles:
        tiles[key] = {
            "schemaVersion": WATERS_SCHEMA_VERSION,
            "tile": key,
            "bounds": list(tile_bounds(*cell)),
            "rivers": [],
            "dams": [],
            "plain": "",
        }
    return tiles[key]


def _tiles(features: WaterFeatures, register: Register, districts: Districts) -> dict[str, dict[str, Any]]:
    tiles: dict[str, dict[str, Any]] = {}
    for river in rivers_of(features.ways):
        row = _river_row(river, register, districts)
        for cell, parts in river_parts(river.lines, WATERS_TOLERANCE).items():
            _tile(tiles, cell)["rivers"].append({**row, "lines": encode_records(parts)})
    for cell, parts in river_parts(features.plain, WATERS_TOLERANCE).items():
        _tile(tiles, cell)["plain"] = encode_records(parts)
    for dam in named_dams(features.dams, features.reservoirs):
        _tile(tiles, cell_of(dam.longitude, dam.latitude))["dams"].append(_dam_row(dam, districts))
    return dict(sorted(tiles.items()))


def waters_build(
    features: WaterFeatures, register: Register, districts: Districts, dataset: Mapping[str, Any]
) -> WatersBuild:
    tiles = _tiles(features, register, districts)
    index = {
        "schemaVersion": WATERS_SCHEMA_VERSION,
        "source": WATERS_SOURCE,
        "site": WATERS_SITE,
        "licence": WATERS_LICENCE,
        "datasets": [dict(dataset)],
        "bounds": list(BOUNDS),
        "tileDegrees": TILE_DEGREES,
        "tolerance": WATERS_TOLERANCE,
        "tiles": [
            {"id": key, "bounds": tile["bounds"], "rivers": len(tile["rivers"]), "dams": len(tile["dams"])}
            for key, tile in tiles.items()
        ],
    }
    return WatersBuild(index=index, tiles=tiles, names=held_names(tiles, dataset))


def tiles_module(tiles: Iterable[str]) -> str:
    return TILES_MODULE.format(rows="".join(TILE_ROW.format(tile=tile) for tile in sorted(tiles)))
