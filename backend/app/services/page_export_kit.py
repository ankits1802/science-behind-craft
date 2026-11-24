from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import replace

from app.research.component_specs_kit import DeclaredDiagramSpec, KitPartSpec, SectionPart
from app.research.component_specs_plates import ColourCard, LabelCardSpec, SwatchCardsSpec
from app.research.component_specs_timeline_map import DeclaredTimelineMapSpec
from app.research.datasets import BOUNDARY_CAPTION

from .export_pdf_text import years_text
from .export_still_figures import swatch_strip
from .export_still_kit import diagram_still
from .export_still_map import MapAsk, MapPin, timeline_still
from .export_stills import Still
from .page_export_figures import FigureAsk, dataset_credit, prefixed, scene_of
from .page_export_model import ExportFigure, ExportText, plain_text

__all__ = [
    "KIT_MOTION_NOTE",
    "kit_diagram_figure",
    "kit_diagram_lines",
    "label_card_figure",
    "swatch_cards_figure",
    "timeline_map_figure",
]

KIT_MOTION_NOTE = "On the page a panel's change plays when pressed; here each panel is drawn at rest."
DRAWN_PREFIX = "Drawn: "
VIA_PREFIX = "→ "
DYE_TOKEN = "--dye-{name}"
TextOf = Callable[[str | None], ExportText | None]


def kit_diagram_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, DeclaredDiagramSpec):
        return None
    lines = [
        ask.unit(spec.head.caption, "note"),
        *kit_diagram_lines(spec, ask.unit),
        ask.unit(spec.alt, "note"),
    ]
    figure = ask.figure([diagram_still(spec)], lines, ask.title(spec.head.title))
    moving = any(panel.motion is not None for panel in spec.panels)
    return replace(figure, note=KIT_MOTION_NOTE) if moving else figure


def kit_diagram_lines(spec: DeclaredDiagramSpec, text_of: TextOf) -> Iterator[ExportText | None]:
    numbered = spec.layout != "section"
    for number, panel in enumerate(spec.panels, start=1):
        label = text_of(panel.label)
        via = text_of(panel.via)
        head = f"{number}. " if numbered else ""
        yield prefixed(head, label)
        if via is not None:
            yield prefixed(VIA_PREFIX, via, "note")
        yield text_of(panel.text)
        yield _parts_line(panel.parts, text_of)


def _parts_line(parts: list[KitPartSpec], text_of: TextOf) -> ExportText | None:
    names = [text.plain.strip() for text in (text_of(ref) for ref in _part_refs(parts)) if text is not None]
    shown = [name for name in dict.fromkeys(names) if name]
    return plain_text(DRAWN_PREFIX + "; ".join(shown), "note") if shown else None


def _part_refs(parts: list[KitPartSpec]) -> Iterator[str]:
    for part in parts:
        yield part.label
        if isinstance(part, SectionPart):
            yield from (layer.label for layer in part.layers)


def timeline_map_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, DeclaredTimelineMapSpec):
        return None
    lines = [ask.unit(spec.head.caption, "note"), *_place_lines(ask, spec), *_route_lines(ask, spec)]
    lines += [ask.unit(fact.text) for fact in spec.undated if fact.place is None]
    lines.append(plain_text(spec.boundary_caption or BOUNDARY_CAPTION, "credit"))
    credits = [dataset_credit(dataset) for dataset in spec.datasets]
    return ask.figure([timeline_still(_map_ask(spec))], lines, ask.title(spec.head.title), credits)


def _map_ask(spec: DeclaredTimelineMapSpec) -> MapAsk:
    found = [place.found for place in spec.places]
    pins = [MapPin(at.longitude, at.latitude, index + 1) for index, at in enumerate(found) if at is not None]
    shown = {pin.number - 1: at for at, pin in enumerate(pins)}
    routes = [(shown[r.start], shown[r.end]) for r in spec.routes if r.start in shown and r.end in shown]
    districts = [at.district_lgd for at in found if at is not None and at.district_lgd is not None]
    homes = [
        place.found.district_lgd
        for place in spec.places
        if place.home and place.found is not None and place.found.district_lgd is not None
    ]
    return MapAsk(pins=pins, routes=routes, districts=districts, homes=homes)


def _place_lines(ask: FigureAsk, spec: DeclaredTimelineMapSpec) -> Iterator[ExportText | None]:
    for index, place in enumerate(spec.places):
        home = " (this craft's place)" if place.home else ""
        yield prefixed(f"{index + 1}. ", _suffixed(ask.unit(place.name), home))
        for point in spec.points:
            if point.place == index:
                yield prefixed(
                    f"{years_text(point.year_from, point.year_to)}: ", ask.unit(point.text), "body"
                )
        for fact in spec.undated:
            if fact.place == index:
                yield ask.unit(fact.text)


def _route_lines(ask: FigureAsk, spec: DeclaredTimelineMapSpec) -> Iterator[ExportText]:
    for route in spec.routes:
        start, end = ask.plain(spec.places[route.start].name), ask.plain(spec.places[route.end].name)
        years = years_text(route.year_from, route.year_to)
        yield prefixed(f"{start} to {end}, {years}: ", ask.unit(route.text))


def _suffixed(text: ExportText | None, suffix: str) -> ExportText | None:
    if text is None or not suffix:
        return text
    return ExportText(runs=(*text.runs, *plain_text(suffix).runs), role=text.role, lang=text.lang)


def swatch_cards_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, SwatchCardsSpec):
        return None
    ask.replaced(spec.chapter_no)
    lines: list[ExportText | None] = [ask.unit(spec.intro)]
    stills: list[Still] = []
    for number, card in enumerate(spec.colours, start=1):
        stills.append(swatch_strip(_card_tokens(card)))
        lines += _card_lines(ask, card, number)
    return ask.figure(stills, lines, ask.title(spec.title))


def _card_tokens(card: ColourCard) -> list[str | None]:
    swatches = [swatch for swatch in (card.before, card.after) if swatch is not None]
    return [DYE_TOKEN.format(name=swatch.dye) for swatch in swatches] or [None]


def _card_lines(ask: FigureAsk, card: ColourCard, number: int) -> list[ExportText | None]:
    swatches = [swatch for swatch in (card.before, card.after) if swatch is not None]
    named = " becomes " if card.join == "becomes" else " or "
    captions = named.join(ask.plain(swatch.caption) for swatch in swatches)
    return [
        prefixed(f"{number}. ", ask.unit(card.name)),
        prefixed("Given by: ", ask.unit(card.agent), "body"),
        ask.unit(card.text),
        ask.unit(card.why),
        plain_text(f"Swatches: {captions}", "note") if captions else None,
    ]


def label_card_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, LabelCardSpec):
        return None
    lines = [ask.unit(spec.kicker, "note"), ask.unit(spec.sentence)]
    for fact in spec.facts:
        lines.append(prefixed(f"{ask.plain(fact.term)}: ", ask.unit(fact.value), "body"))
    seal = scene_of((ask.spec or {}).get("seal"))
    return ask.figure([seal], lines, ask.entry.title)
