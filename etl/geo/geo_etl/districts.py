import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import make_valid

DATA = Path(__file__).resolve().parent.parent / "data"
SHAPES_PATH = DATA / "district-shapes.json"
REGISTER_PATH = DATA / "lgd_register.json"
SHAPES_SHA256 = "aec1d4c75d9ba77acdc18b223f3382aca5c6ead9724bb263ad62b09079aad417"
REGISTER_SHA256 = "ce841e1855ee460dbc0933467cd6932f5eb9e052972c9ea74f474f9ce8821f87"

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
LOOKUP = {ch: i for i, ch in enumerate(ALPHABET)}
SCALE = 1000
INDIA_LCC = "EPSG:7755"


@dataclass(frozen=True)
class Register:
    states: dict[int, str]
    districts: dict[int, tuple[int, str]]
    pending: list[dict]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_rings(payload: str) -> list[list[tuple[float, float]]]:
    out: list[list[tuple[float, float]]] = []
    index = 0
    x = y = 0

    def read() -> int:
        nonlocal index
        shift = result = 0
        while True:
            value = LOOKUP[payload[index]]
            index += 1
            result |= (value & 0x1F) << shift
            shift += 5
            if value < 0x20:
                break
        return ~(result >> 1) if result & 1 else result >> 1

    while index < len(payload):
        count = read()
        if count <= 0:
            break
        points: list[tuple[float, float]] = []
        for _ in range(count):
            x += read()
            y += read()
            points.append((x / SCALE, y / SCALE))
        out.append(points)
    return out


def assemble(encoded_rings: list[str]) -> BaseGeometry:
    polygons: list[Polygon] = []
    for encoded in encoded_rings:
        for points in decode_rings(encoded):
            if len(points) >= 3:
                polygon = make_valid(Polygon(points))
                if not polygon.is_empty:
                    polygons.append(polygon)
    polygons.sort(key=lambda p: p.area, reverse=True)
    shape: BaseGeometry | None = None
    for polygon in polygons:
        shape = polygon if shape is None else shape.symmetric_difference(polygon)
    if shape is None:
        return Polygon()
    return make_valid(unary_union([shape]))


def load_register(path: Path = REGISTER_PATH) -> Register:
    raw = json.loads(path.read_text(encoding="utf-8"))
    states = {int(s["lgd"]): s["name"] for s in raw["states"]}
    districts = {int(d["lgd"]): (int(d["stateLgd"]), d["name"]) for d in raw["districts"]}
    return Register(states=states, districts=districts, pending=list(raw.get("pending", [])))


def verify_inputs() -> None:
    for path, expected in ((SHAPES_PATH, SHAPES_SHA256), (REGISTER_PATH, REGISTER_SHA256)):
        actual = sha256_of(path)
        if actual != expected:
            raise SystemExit(f"{path.name}: sha256 {actual} does not match the vendored {expected}")


def load_districts(lgds: set[int] | None = None, states: set[int] | None = None) -> gpd.GeoDataFrame:
    verify_inputs()
    register = load_register()
    raw = json.loads(SHAPES_PATH.read_text(encoding="utf-8"))
    rows = []
    for row in raw["districts"]:
        lgd = int(row["lgd"])
        state_lgd = int(row["stateLgd"])
        if lgds and lgd not in lgds:
            continue
        if states and state_lgd not in states:
            continue
        geometry = assemble(row["rings"])
        if geometry.is_empty:
            continue
        name = register.districts.get(lgd, (state_lgd, ""))[1]
        rows.append(
            {
                "districtLgd": lgd,
                "stateLgd": state_lgd,
                "districtName": name,
                "stateName": register.states.get(state_lgd, ""),
                "centroidLon": float(row["centroid"][0]),
                "centroidLat": float(row["centroid"][1]),
                "geometry": geometry,
            }
        )
    columns = ["districtLgd", "stateLgd", "districtName", "stateName", "centroidLon", "centroidLat", "geometry"]
    frame = gpd.GeoDataFrame(pd.DataFrame(rows, columns=columns), geometry="geometry", crs="EPSG:4326")
    if len(frame):
        frame["areaKm2"] = frame.to_crs(INDIA_LCC).area / 1e6
    else:
        frame["areaKm2"] = []
    return frame.sort_values("districtLgd").reset_index(drop=True)


def districts_without_shapes() -> list[dict]:
    register = load_register()
    raw = json.loads(SHAPES_PATH.read_text(encoding="utf-8"))
    drawn = {int(row["lgd"]) for row in raw["districts"]}
    missing = [
        {"districtLgd": lgd, "stateLgd": state, "districtName": name, "reason": "no polygon in district-shapes.json"}
        for lgd, (state, name) in sorted(register.districts.items())
        if lgd not in drawn
    ]
    missing.extend(
        {"districtLgd": None, "stateName": p.get("state"), "districtName": p.get("district"), "reason": p.get("reason")}
        for p in register.pending
    )
    return missing
