from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace

from app.data.dataset_registry import registry_rows
from app.data.map_layers import held_base
from app.geo.datasets import registry_row_ref
from app.geo.map_base import BaseAsk, BaseShapes, BaseSources, SiteBox, base_shapes, draws_district_lines
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
    token_colour,
)
from .place_ground import stored_layers

__all__ = [
    "MAP_PRINT_PIXELS",
    "PaperPin",
    "base_datasets",
    "base_sources",
    "base_still",
    "base_unit",
    "on_base",
    "pinned_still",
]

MAP_PRINT_PIXELS = 1800
LINE_UNITS = 400.0
PIN_SHARE = 0.009
NUMBER_SHARE = 0.02
RELIEF_STEPS = 7
RELIEF_CODE = "ETOPO1_ICE"
RIVERS_CODE = "NATURAL_EARTH_10M_PHYSICAL"
WIDTHS = {"river": 0.7, "district": 0.35, "state": 0.65, "home": 1.2, "outline": 0.9, "route": 1.4}


@dataclass(frozen=True)
class PaperPin:
    at: Point
    number: int


def base_still(box: SiteBox, ask: BaseAsk) -> Still:
    shapes = base_shapes(stored_layers(), base_sources(), box, ask)
    unit = box.width / LINE_UNITS
    paths = tuple(_painted(shapes, ask, unit))
    return Still(width=box.width, height=box.height, paths=paths, pixels=MAP_PRINT_PIXELS)


def on_base(figure: Still, box: SiteBox, ask: BaseAsk) -> Still:
    drawn = merged(box.width, box.height, [(base_still(box, ask), IDENTITY), (figure, IDENTITY)])
    return replace(drawn, pixels=MAP_PRINT_PIXELS)


def pinned_still(
    box: SiteBox, ask: BaseAsk, pins: Sequence[PaperPin], routes: Sequence[tuple[int, int]]
) -> Still:
    base = base_still(box, ask)
    radius, size = box.width * PIN_SHARE, box.width * NUMBER_SHARE
    placed = {pin.number: (pin.at[0] - box.x, pin.at[1] - box.y) for pin in pins}
    route = _colour("--map-selection")
    lines = [
        StillPath(
            points=(placed[start], placed[end]),
            closed=False,
            line=route,
            width=WIDTHS["route"] * base_unit(box),
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
    return replace(base, paths=(*base.paths, *lines, *marks), texts=tuple(texts))


def base_unit(box: SiteBox) -> float:
    return box.width / LINE_UNITS


def base_datasets(box: SiteBox, ask: BaseAsk) -> list[DatasetRef]:
    codes = [
        *([RELIEF_CODE] if ask.relief else []),
        *([RIVERS_CODE] if ask.rivers else []),
        BOUNDARY_DATASET_CODE,
    ]
    rows = {str(row["code"]): row for row in registry_rows()}
    shown = codes if ask.homes or draws_district_lines(box, ask.districts) else codes[:-1]
    return [registry_row_ref(rows[code]) for code in shown]


def base_sources() -> BaseSources:
    files = held_base()
    return BaseSources(outline=files.outline, states=files.states, districts=files.districts)


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


def _stroke(points: tuple[Point, ...], colour: Colour, width: float) -> StillPath:
    return StillPath(points=points, closed=False, line=colour, width=width)


def _colour(token: str) -> Colour:
    found = token_colour(token)
    if found is None:
        raise ValueError(f"the design system names no {token}")
    return found
