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
from .waters_register import Register, accepted_names

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

WATERS_SCHEMA_VERSION = 1
WATERS_SOURCE = "OpenStreetMap rivers, streams and dams, India extract by Geofabrik"
WATERS_SITE = "https://www.openstreetmap.org/copyright"
WATERS_LICENCE = "ODbL 1.0"
TILES_MODULE = (
    'import type { WatersTile } from "@/lib/mapWaters";\n\n'
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
    agreed = register.agreeing(river.name, crossed)
    row: dict[str, Any] = {"id": river.id, "name": river.name, "kind": river.kind, "districts": crossed}
    also = [name for name in accepted_names(river.name, agreed) if name != river.name]
    if also:
        row["also"] = also
    if agreed:
        row["agrees"] = [{"name": found.name, "source": found.source} for found in agreed]
    return row


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
        }
    return tiles[key]


def _tiles(
    rivers: Iterable[River], dams: Iterable[Dam], register: Register, districts: Districts
) -> dict[str, dict[str, Any]]:
    tiles: dict[str, dict[str, Any]] = {}
    for river in rivers:
        row = _river_row(river, register, districts)
        for cell, parts in river_parts(river, WATERS_TOLERANCE).items():
            _tile(tiles, cell)["rivers"].append({**row, "lines": encode_records(parts)})
    for dam in dams:
        _tile(tiles, cell_of(dam.longitude, dam.latitude))["dams"].append(_dam_row(dam, districts))
    return dict(sorted(tiles.items()))


def _names(tiles: Mapping[str, Mapping[str, Any]], dataset: Mapping[str, Any]) -> dict[str, Any]:
    rivers = {
        name
        for tile in tiles.values()
        for row in tile["rivers"]
        for name in (row["name"], *row.get("also", []))
    }
    dams = {row["name"] for tile in tiles.values() for row in tile["dams"]}
    return {
        "schemaVersion": WATERS_SCHEMA_VERSION,
        "datasets": [dict(dataset)],
        "rivers": sorted(rivers),
        "dams": sorted(dams),
    }


def waters_build(
    features: WaterFeatures, register: Register, districts: Districts, dataset: Mapping[str, Any]
) -> WatersBuild:
    dams = named_dams(features.dams, features.reservoirs)
    tiles = _tiles(rivers_of(features.ways), dams, register, districts)
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
    return WatersBuild(index=index, tiles=tiles, names=_names(tiles, dataset))


def tiles_module(tiles: Iterable[str]) -> str:
    return TILES_MODULE.format(rows="".join(TILE_ROW.format(tile=tile) for tile in sorted(tiles)))
