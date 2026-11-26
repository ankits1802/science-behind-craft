from __future__ import annotations

import math
import re
from collections.abc import Iterator, Sequence

from app.geo.ground_measure import KM_PER_DEGREE
from app.geo.map_base import BaseAsk, SiteBox, named_points, projected_frame, site_point
from app.geo.map_waters import WaterAsk
from app.research.component_specs_general import GeneralMapLayerSpec
from app.research.datasets import BOUNDARY_CAPTION

from .export_map_base import PaperPin, base_sources, paper_base, pinned_still
from .page_export_figures import FigureAsk, dataset_credit, prefixed
from .page_export_model import ExportFigure, ExportText, plain_text

__all__ = ["home_districts", "places_box", "places_map_figure"]

PLACES_ZOOM = (0.035, 0.25)
NAMED_ZOOM = (0.035, 0.06)
HOME_SUBJECT = re.compile(r"^place:lgd:(\d+)$")

Point = tuple[float, float]


def places_map_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, GeneralMapLayerSpec):
        return None
    box = places_box(spec)
    base = BaseAsk(relief=True, rivers=True, districts=False, homes=tuple(home_districts(ask.entry.subjects)))
    pins = [
        PaperPin(site_point(place.longitude, place.latitude), at) for at, place in enumerate(spec.places, 1)
    ]
    routes = [(route.start + 1, route.end + 1) for route in spec.routes or []]
    paper = paper_base(box, base, _water_ask(spec))
    lines = [
        ask.unit(spec.head.caption, "note"),
        *_place_lines(ask, spec),
        *_part_lines(ask, spec),
        plain_text(BOUNDARY_CAPTION, "credit"),
    ]
    credits = [dataset_credit(dataset) for dataset in paper.datasets]
    return ask.figure([pinned_still(paper, pins, routes)], lines, ask.title(spec.head.title), credits)


def places_box(spec: GeneralMapLayerSpec) -> SiteBox:
    frame = spec.frame
    if frame is not None and (frame.district is not None or frame.state is not None):
        named = named_points(base_sources(), district=frame.district, state=frame.state)
        if named:
            return _framed(named, NAMED_ZOOM)
    chosen = frame.places if frame is not None and frame.places else list(range(len(spec.places)))
    points: list[Point] = [(spec.places[at].longitude, spec.places[at].latitude) for at in chosen]
    for ring in spec.rings or []:
        if ring.place in chosen:
            points += _ring_corners(points[chosen.index(ring.place)], ring.radius_km)
    return _framed(points, PLACES_ZOOM)


def _water_ask(spec: GeneralMapLayerSpec) -> WaterAsk:
    emphasis = spec.emphasis
    if emphasis is None:
        return WaterAsk()
    return WaterAsk(rivers=tuple(emphasis.rivers), dams=tuple(emphasis.dams))


def home_districts(subjects: Sequence[str]) -> list[int]:
    found = (HOME_SUBJECT.match(subject) for subject in subjects)
    return list(dict.fromkeys(int(match.group(1)) for match in found if match))


def _framed(points: Sequence[Point], zoom: tuple[float, float]) -> SiteBox:
    projected = [site_point(longitude, latitude) for longitude, latitude in points]
    return projected_frame(projected, min_share=zoom[0], padding_share=zoom[1])


def _ring_corners(centre: Point, radius_km: float) -> list[Point]:
    longitude, latitude = centre
    north_south = radius_km / KM_PER_DEGREE
    east_west = north_south / max(math.cos(math.radians(latitude)), 1e-6)
    return [(longitude - east_west, latitude - north_south), (longitude + east_west, latitude + north_south)]


def _place_lines(ask: FigureAsk, spec: GeneralMapLayerSpec) -> Iterator[ExportText | None]:
    label = ask.plain(spec.value_label)
    for number, place in enumerate(spec.places, start=1):
        yield prefixed(f"{number}. ", ask.unit(place.name))
        if place.value is not None and label:
            yield plain_text(f"{label}: {place.value:g}")
        yield ask.unit(place.reading)


def _part_lines(ask: FigureAsk, spec: GeneralMapLayerSpec) -> Iterator[ExportText | None]:
    for route in spec.routes or []:
        yield prefixed(f"{route.start + 1} → {route.end + 1}: ", ask.unit(route.text))
    for ring in spec.rings or []:
        yield prefixed(f"{ring.place + 1}, {ring.radius_km:g} km: ", ask.unit(ring.text))
    if spec.districts is not None:
        yield ask.unit(spec.districts.value_label, "note")
        yield from (ask.unit(value.reading) for value in spec.districts.values)
    for number, step in enumerate(spec.sequence or [], start=1):
        yield prefixed(f"{number}. ", ask.unit(step.text), "note")
