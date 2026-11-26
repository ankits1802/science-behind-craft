from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from maplayers.waters_register import RegisterRiver, register_of

geometry = pytest.importorskip("shapely.geometry")
pytest.importorskip("geo_etl.osm_rivers")
waters = pytest.importorskip("maplayers.waters")
built = pytest.importorskip("maplayers.waters_body")

RECORD = "\x1e"
KACHCHH = 449
JAIPUR = 102
DATASET = {"code": "OSM_WATERWAYS", "readOn": "2026-11-26"}


def _line(*points: tuple[float, float]) -> dict[str, Any]:
    return {"type": "LineString", "coordinates": [list(point) for point in points]}


def _area(west: float, south: float, east: float, north: float) -> dict[str, Any]:
    ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
    return {"type": "Polygon", "coordinates": [ring]}


FEATURES = [
    ("w101", {"waterway": "stream", "name": "Dhamadka"}, _line((70.12, 23.25), (70.12, 23.30))),
    ("w102", {"waterway": "stream", "name": "Dhamadka"}, _line((70.12, 23.30), (70.13, 23.36))),
    ("w103", {"waterway": "stream", "name": "Dhamadka"}, _line((75.0, 26.0), (75.1, 26.1))),
    ("w104", {"waterway": "river", "name": "Khari"}, _line((70.12, 23.30), (70.20, 23.30))),
    ("w105", {"waterway": "river"}, _line((70.0, 23.0), (70.1, 23.0))),
    ("w106", {"waterway": "river", "name": "धमडका"}, _line((70.0, 23.1), (70.1, 23.1))),
    ("w201", {"waterway": "dam"}, _line((70.10, 23.245), (70.14, 23.245))),
    ("w202", {"waterway": "dam", "name": "Kanota Dam"}, _line((75.93, 26.91), (75.94, 26.91))),
    ("w203", {"waterway": "dam"}, _line((72.0, 21.0), (72.01, 21.0))),
    ("n204", {"waterway": "dam"}, {"type": "Point", "coordinates": [73.0, 22.0]}),
    ("w205", {"waterway": "dam"}, _line((74.0, 22.0), (74.0, 22.02))),
    (
        "a602",
        {"natural": "water", "water": "reservoir", "name": "Tappar Reservoir"},
        _area(70.10, 23.245, 70.14, 23.27),
    ),
    (
        "a604",
        {"natural": "water", "water": "reservoir", "name": "Alpha Lake"},
        _area(73.99, 22.0, 74.0, 22.02),
    ),
    (
        "a606",
        {"natural": "water", "water": "reservoir", "name": "Beta Reservoir"},
        _area(74.0, 22.0, 74.01, 22.02),
    ),
    ("a608", {"natural": "water", "water": "reservoir"}, _area(76.0, 20.0, 76.1, 20.1)),
    ("a611", {"landuse": "reservoir", "name": "Gamma Reservoir"}, _area(77.0, 20.0, 77.1, 20.1)),
]


def _export(folder: Path) -> Path:
    path = folder / "india-waters.geojsonseq"
    lines = [
        RECORD + json.dumps({"type": "Feature", "id": ref, "properties": tags, "geometry": shape}) + "\n"
        for ref, tags, shape in FEATURES
    ]
    path.write_text("".join(lines), encoding="utf-8")
    return path


def _districts(shape: Any) -> list[int]:
    return [KACHCHH] if shape.bounds[0] < 71 else [JAIPUR]


def test_an_osm_id_reads_as_its_type_and_number() -> None:
    assert waters.osm_ref("w141195150") == "way/141195150"
    assert waters.osm_ref("n12") == "node/12"
    assert waters.osm_ref("r7") == "relation/7"
    assert waters.osm_ref("a1122080054") == "way/561040027"
    assert waters.osm_ref("a611") == "relation/305"
    assert waters.osm_ref("x12") is None
    assert waters.osm_ref("w12x") is None


def test_rivers_and_streams_by_name_dams_named_reservoirs_and_unnamed_rivers_are_read(tmp_path: Path) -> None:
    found = waters.read_features(_export(tmp_path))
    assert [way.way for way in found.ways] == [101, 102, 103, 104]
    assert [dam.ref for dam in found.dams] == ["way/201", "way/202", "way/203", "node/204", "way/205"]
    names = ["Tappar Reservoir", "Alpha Lake", "Beta Reservoir", "Gamma Reservoir"]
    assert [reservoir.name for reservoir in found.reservoirs] == names
    assert [reservoir.ref for reservoir in found.reservoirs] == [
        "way/301",
        "way/302",
        "way/303",
        "relation/305",
    ]
    assert [list(line.coords) for line in found.plain] == [
        [(70.0, 23.0), (70.1, 23.0)],
        [(70.0, 23.1), (70.1, 23.1)],
    ]


def test_ways_of_one_name_that_meet_end_to_end_are_one_river(tmp_path: Path) -> None:
    rivers = waters.rivers_of(waters.read_features(_export(tmp_path)).ways)
    assert [(river.id, river.name, river.kind, len(river.lines)) for river in rivers] == [
        (101, "Dhamadka", "stream", 2),
        (103, "Dhamadka", "stream", 1),
        (104, "Khari", "river", 1),
    ]


def test_a_dam_takes_its_own_name_or_that_of_the_one_reservoir_it_holds(tmp_path: Path) -> None:
    found = waters.read_features(_export(tmp_path))
    dams = waters.named_dams(found.dams, found.reservoirs)
    assert [(dam.ref, dam.name, dam.named_by, dam.longitude, dam.latitude) for dam in dams] == [
        ("way/202", "Kanota Dam", "dam", 75.935, 26.91),
        ("way/201", "Tappar Reservoir", "reservoir", 70.12, 23.245),
    ]


def test_a_river_is_cut_into_the_two_degree_tiles_it_crosses() -> None:
    assert waters.cell_of(70.13, 23.25) == (70, 22)
    assert waters.cell_of(69.99, 23.25) == (68, 22)
    assert waters.tile_id(70, 6) == "e070n06"
    assert waters.tile_bounds(64, 4) == (64.7, 5.3, 66.0, 6.0)
    line = geometry.LineString([(69.5, 23.1), (70.5, 23.1)])
    parts = waters.river_parts((line,), waters.WATERS_TOLERANCE)
    assert sorted(parts) == [(68, 22), (70, 22)]
    assert sorted(parts[(68, 22)][0]) == [(69.5, 23.1), (70.0, 23.1)]
    assert sorted(parts[(70, 22)][0]) == [(70.0, 23.1), (70.5, 23.1)]


def test_a_build_names_each_river_by_the_dataset_and_by_the_register_where_they_agree(tmp_path: Path) -> None:
    register = register_of([RegisterRiver("Dhamadka River (Suran)", frozenset({KACHCHH}), "Kutch-Ajrakh")])
    done = built.waters_build(waters.read_features(_export(tmp_path)), register, _districts, DATASET)
    assert list(done.tiles) == ["e070n22", "e074n26"]
    kachchh = {row["id"]: row for row in done.tiles["e070n22"]["rivers"]}
    assert kachchh[101]["also"] == ["Dhamadka River", "Dhamadka River (Suran)", "Suran"]
    assert kachchh[101]["agrees"] == [{"name": "Dhamadka River (Suran)", "source": "Kutch-Ajrakh"}]
    assert "also" not in kachchh[104] and "agrees" not in kachchh[104]
    jaipur = done.tiles["e074n26"]["rivers"]
    assert [(row["id"], row["districts"]) for row in jaipur] == [(103, [JAIPUR])]
    assert "also" not in jaipur[0]
    assert [dam["name"] for dam in done.tiles["e070n22"]["dams"]] == ["Tappar Reservoir"]
    assert done.names["rivers"] == ["Dhamadka", "Dhamadka River", "Dhamadka River (Suran)", "Khari", "Suran"]
    assert done.names["dams"] == ["Kanota Dam", "Tappar Reservoir"]
    assert [(tile["id"], tile["rivers"], tile["dams"]) for tile in done.index["tiles"]] == [
        ("e070n22", 2, 1),
        ("e074n26", 1, 1),
    ]
    assert done.index["datasets"] == [DATASET]
    assert done.tiles["e070n22"]["plain"] and done.tiles["e074n26"]["plain"] == ""


def test_the_server_imports_each_tile_by_its_own_literal_path() -> None:
    module = built.tiles_module(["e074n26", "e070n22"])
    assert module.splitlines()[3:5] == [
        '  e070n22: () => import("@/public/layers/waters/e070n22.json").then((tile) => tile.default),',
        '  e074n26: () => import("@/public/layers/waters/e074n26.json").then((tile) => tile.default),',
    ]
    assert module.startswith('import type { WatersTile } from "@/lib/mapWaters";\n')
