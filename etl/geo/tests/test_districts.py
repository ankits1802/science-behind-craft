import json

import pytest
from shapely.geometry import GeometryCollection, LineString, Point, box

from geo_etl.districts import (
    ALPHABET,
    SHAPES_PATH,
    assemble,
    decode_rings,
    districts_without_shapes,
    load_districts,
    load_register,
    polygonal_part,
    verify_inputs,
)

MAHE_RINGS = ["IkxzEm_WiBzCzBXagC", "GwxzEy7WdFSQ"]
SLIVERED = {304: 19, 308: 19, 449: 24, 586: 33, 673: 24, 675: 24, 747: 28}


def encode_number(value: int) -> str:
    value = ~(value << 1) if value < 0 else value << 1
    out = ""
    while value >= 0x20:
        out += ALPHABET[0x20 | (value & 0x1F)]
        value >>= 5
    return out + ALPHABET[value]


def encode_ring(points: list[tuple[int, int]], start: tuple[int, int] = (0, 0)) -> str:
    x, y = start
    text = encode_number(len(points))
    for px, py in points:
        text += encode_number(px - x) + encode_number(py - y)
        x, y = px, py
    return text


def test_decode_rings_mahe_outer():
    assert decode_rings(MAHE_RINGS[0]) == [[(75.538, 11.763), (75.555, 11.721), (75.529, 11.709), (75.542, 11.741)]]


def test_decode_rings_mahe_hole():
    assert decode_rings(MAHE_RINGS[1]) == [[(75.544, 11.705), (75.529, 11.702), (75.538, 11.71)]]


def test_decode_rings_round_trip_with_negative_deltas():
    points = [(1000, 2000), (-500, 2500), (-500, -750), (0, 0)]
    assert decode_rings(encode_ring(points)) == [[(1.0, 2.0), (-0.5, 2.5), (-0.5, -0.75), (0.0, 0.0)]]


def test_decode_rings_stops_at_zero_count():
    payload = encode_ring([(1000, 1000), (2000, 1000), (2000, 2000)]) + encode_number(0) + "AAAA"
    assert len(decode_rings(payload)) == 1


def test_decode_rings_empty():
    assert decode_rings("") == []


def test_assemble_drops_degenerate_rings():
    shape = assemble([encode_ring([(0, 0), (1000, 0)])])
    assert shape.is_empty


def test_assemble_drops_a_collapsed_spike_and_keeps_the_area():
    square_with_spike = [(0, 0), (2000, 0), (2000, 2000), (3000, 3000), (2000, 2000), (0, 2000)]
    shape = assemble([encode_ring(square_with_spike)])
    assert shape.geom_type == "Polygon"
    assert shape.area == pytest.approx(4.0)
    assert shape.bounds == pytest.approx((0.0, 0.0, 2.0, 2.0))


def test_polygonal_part_keeps_every_polygon_of_a_mixed_collection():
    mixed = GeometryCollection([box(0, 0, 1, 1), box(5, 5, 7, 7), LineString([(1, 1), (5, 5)]), Point(9, 9)])
    shape = polygonal_part(mixed)
    assert shape.geom_type == "MultiPolygon"
    assert shape.area == pytest.approx(5.0)
    assert polygonal_part(LineString([(0, 0), (1, 1)])).is_empty


def test_every_vendored_district_loads_as_a_polygon_or_multipolygon():
    raw = json.loads(SHAPES_PATH.read_text(encoding="utf-8"))
    frame = load_districts()
    assert len(frame) == len(raw["districts"])
    assert set(frame.geometry.geom_type) <= {"Polygon", "MultiPolygon"}


def test_districts_with_collapsed_slivers_load_as_multipolygons():
    frame = load_districts(set(SLIVERED))
    assert dict(zip(frame["districtLgd"], frame["stateLgd"], strict=True)) == SLIVERED
    assert set(frame.geometry.geom_type) == {"MultiPolygon"}


def test_assemble_mahe_is_valid():
    shape = assemble(MAHE_RINGS)
    assert shape.is_valid
    assert not shape.is_empty
    assert shape.bounds == pytest.approx((75.529, 11.702, 75.555, 11.763))


def test_load_register_names_mahe():
    register = load_register()
    assert register.districts[599] == (34, "Mahe")
    assert register.states[34] == "Puducherry"


def test_verify_inputs_accepts_vendored_files():
    verify_inputs()


def test_load_districts_mahe():
    frame = load_districts({599})
    assert len(frame) == 1
    row = frame.iloc[0]
    assert int(row["districtLgd"]) == 599
    assert int(row["stateLgd"]) == 34
    assert row["districtName"] == "Mahe"
    assert row["stateName"] == "Puducherry"
    assert (row["centroidLon"], row["centroidLat"]) == (75.544, 11.721)
    assert 4.0 < row["areaKm2"] < 8.0
    assert frame.crs.to_epsg() == 4326
    assert row.geometry.is_valid
    assert row.geometry.contains(Point(75.544, 11.721))


def test_load_districts_state_filter():
    frame = load_districts(states={34})
    assert 599 in set(frame["districtLgd"])
    assert set(frame["stateLgd"]) == {34}
    assert list(frame["districtLgd"]) == sorted(frame["districtLgd"])


def test_load_districts_no_match_is_empty():
    frame = load_districts({-1})
    assert frame.empty
    assert "areaKm2" in frame.columns


def test_districts_without_shapes_rows_have_reason():
    for item in districts_without_shapes():
        assert item["reason"]
        assert "districtName" in item
