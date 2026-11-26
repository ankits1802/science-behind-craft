from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from functools import cache

from app.data.dataset_registry import registry_rows
from app.data.map_layers import held_base
from app.data.water_tiles import held_water_tile, held_waters_index
from app.geo.datasets import registry_row_ref
from app.geo.map_base import BaseAsk, BaseShapes, BaseSources, SiteBox, base_shapes, draws_district_lines
from app.geo.map_waters import (
    NO_WATERS,
    WaterAsk,
    WaterShapes,
    WaterTile,
    tiles_in_box,
    water_shapes,
    water_tile,
)
from app.research.datasets import BOUNDARY_DATASET_CODE, DatasetRef

from .export_stills import (
    IDENTITY,
    WHITE,
    Colour,
    Point,
    Still,
    StillPath,
    StillText,
    ellipse_points,
    ink,
    merged,
    rect_points,
    token_colour,
)
from .place_ground import stored_layers

__all__ = [
    "MAP_PRINT_PIXELS",
    "PaperBase",
    "PaperPin",
    "base_sources",
    "on_base",
    "paper_base",
    "pinned_still",
]

MAP_PRINT_PIXELS = 1800
LINE_UNITS = 400.0
PIN_SHARE = 0.009
NUMBER_SHARE = 0.02
WATER_LABEL_SHARE = 0.016
DAM_SHARE = 0.012
LABEL_LIFT = 0.55
LABEL_GAP = 1.6
RELIEF_STEPS = 7
RELIEF_CODE = "ETOPO1_ICE"
RIVERS_CODE = "NATURAL_EARTH_10M_PHYSICAL"
WATERS_CODE = "OSM_WATERWAYS"
WIDTHS = {
    "river": 0.7,
    "water": 0.45,
    "strong": 1.6,
    "halo": 3.4,
    "district": 0.35,
    "state": 0.65,
    "home": 1.2,
    "outline": 0.9,
    "route": 1.4,
}


@dataclass(frozen=True)
class PaperPin:
    at: Point
    number: int


@dataclass(frozen=True)
class PaperBase:
    box: SiteBox
    still: Still
    datasets: tuple[DatasetRef, ...]


def paper_base(box: SiteBox, ask: BaseAsk, waters: WaterAsk | None = None) -> PaperBase:
    shapes = base_shapes(stored_layers(), base_sources(), box, ask)
    small = _small_waters(box, waters)
    unit = box.width / LINE_UNITS
    paths = (*_painted(shapes, ask, unit), *_water_paths(small, box, unit))
    still = Still(
        width=box.width,
        height=box.height,
        paths=paths,
        texts=_water_texts(small, box),
        pixels=MAP_PRINT_PIXELS,
    )
    return PaperBase(box=box, still=still, datasets=_datasets(box, ask, small))


def on_base(figure: Still, base: PaperBase) -> Still:
    drawn = merged(base.box.width, base.box.height, [(base.still, IDENTITY), (figure, IDENTITY)])
    return replace(drawn, pixels=MAP_PRINT_PIXELS)


def pinned_still(base: PaperBase, pins: Sequence[PaperPin], routes: Sequence[tuple[int, int]]) -> Still:
    box = base.box
    radius, size = box.width * PIN_SHARE, box.width * NUMBER_SHARE
    placed = {pin.number: (pin.at[0] - box.x, pin.at[1] - box.y) for pin in pins}
    route = _colour("--map-selection")
    lines = [
        StillPath(
            points=(placed[start], placed[end]),
            closed=False,
            line=route,
            width=WIDTHS["route"] * box.width / LINE_UNITS,
        )
        for start, end in routes
        if start in placed and end in placed
    ]
    marks = [
        StillPath(points=ellipse_points(*at, radius, radius), fill=_colour("--map-marker"), line=ink(1))
        for at in placed.values()
    ]
    texts = [
        StillText(at=(x + radius * 1.4, y + size / 3), text=str(number), size=size, colour=ink(1))
        for number, (x, y) in placed.items()
    ]
    return replace(base.still, paths=(*base.still.paths, *lines, *marks), texts=(*base.still.texts, *texts))


def base_sources() -> BaseSources:
    files = held_base()
    return BaseSources(outline=files.outline, states=files.states, districts=files.districts)


def _datasets(box: SiteBox, ask: BaseAsk, small: WaterShapes) -> tuple[DatasetRef, ...]:
    boundaries = ask.homes or draws_district_lines(box, ask.districts)
    codes = [
        *([RELIEF_CODE] if ask.relief else []),
        *([RIVERS_CODE] if ask.rivers else []),
        *([WATERS_CODE] if small.drawn else []),
        *([BOUNDARY_DATASET_CODE] if boundaries else []),
    ]
    rows = {str(row["code"]): row for row in registry_rows()}
    return tuple(registry_row_ref(rows[code]) for code in codes)


def _small_waters(box: SiteBox, ask: WaterAsk | None) -> WaterShapes:
    if ask is None:
        return NO_WATERS
    tiles = [_tile(tile_id) for tile_id in tiles_in_box(held_waters_index()["tiles"], box)]
    return water_shapes(tiles, box, ask)


@cache
def _tile(tile_id: str) -> WaterTile:
    return water_tile(held_water_tile(tile_id))


def _painted(shapes: BaseShapes, ask: BaseAsk, unit: float) -> Iterator[StillPath]:
    land = _colour("--elevation-1" if ask.relief else "--map-land")
    yield from (StillPath(points=ring, fill=land) for ring in shapes.land)
    for step, band in shapes.relief:
        fill = _colour(f"--elevation-{min(step, RELIEF_STEPS)}")
        yield from (StillPath(points=ring, fill=fill) for ring in band)
    yield from (StillPath(points=ring, fill=WHITE) for ring in shapes.holes)
    yield from (StillPath(points=ring, fill=_colour("--map-water")) for ring in shapes.lakes)
    strokes = (
        ("--map-river", "river", tuple(line for _, line in shapes.rivers)),
        ("--map-border-district", "district", shapes.districts),
        ("--map-border-state", "state", shapes.states),
        ("--terracotta", "home", shapes.homes),
        ("--map-border-intl", "outline", shapes.coast),
    )
    for token, kind, lines in strokes:
        colour, width = _colour(token), WIDTHS[kind] * unit
        yield from (_stroke(line, colour, width) for line in lines)


def _water_paths(small: WaterShapes, box: SiteBox, unit: float) -> Iterator[StillPath]:
    river = _colour("--map-river")
    yield from (_stroke(line, river, WIDTHS["water"] * unit) for line in small.lines)
    for named in small.strong:
        yield from (_stroke(line, _colour("--map-label-halo"), WIDTHS["halo"] * unit) for line in named.lines)
        yield from (_stroke(line, river, WIDTHS["strong"] * unit) for line in named.lines)
    size = box.width * DAM_SHARE
    for dam in small.dams:
        x, y = dam.at
        yield StillPath(
            points=rect_points(x - size, y - size / 3, size * 2, size * 2 / 3),
            fill=_colour("--map-label"),
            line=_colour("--map-label-halo"),
            width=unit,
        )


def _water_texts(small: WaterShapes, box: SiteBox) -> tuple[StillText, ...]:
    size = box.width * WATER_LABEL_SHARE
    rivers = (
        StillText(
            at=(named.at[0], named.at[1] - size * LABEL_LIFT),
            text=named.name,
            size=size,
            colour=_colour("--map-water-label"),
            anchor="middle",
        )
        for named in small.strong
    )
    dams = (
        StillText(
            at=(dam.at[0] + box.width * DAM_SHARE * LABEL_GAP, dam.at[1] + size / 3),
            text=dam.name,
            size=size,
            colour=_colour("--map-label"),
        )
        for dam in small.dams
    )
    return (*rivers, *dams)


def _stroke(points: tuple[Point, ...], colour: Colour, width: float) -> StillPath:
    return StillPath(points=points, closed=False, line=colour, width=width)


def _colour(token: str) -> Colour:
    found = token_colour(token)
    if found is None:
        raise ValueError(f"the design system names no {token}")
    return found
