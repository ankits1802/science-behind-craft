from __future__ import annotations

from collections.abc import Callable

from app.research.blocks_journey import TimelineMapBlock
from app.research.component_specs_kit import DeclaredDiagramSpec

from .export_pdf_still import draw_still
from .export_pdf_styles import CELL, FIGURE_GAP_MM, FIGURE_TITLE, KICKER, NOTE
from .export_still_kit import diagram_still
from .export_still_map import MapAsk, MapPin, timeline_still
from .page_export_kit import kit_diagram_lines
from .page_export_model import ExportText, plain_text
from .pdf_writer import PdfWriter

__all__ = ["KIT_FIGURE_KICKER", "KIT_STILL_MM", "kit_figure_pdf", "timeline_places_pdf"]

KIT_FIGURE_KICKER = "Figure"
KIT_STILL_MM = 70.0
PLACES_LABEL = "Places on the map"
LabelText = Callable[[str | None], str | None]


def kit_figure_pdf(writer: PdfWriter, spec: DeclaredDiagramSpec, text_of: LabelText) -> None:
    def shown(ref: str | None) -> ExportText | None:
        text = text_of(ref)
        return plain_text(text) if text else None

    writer.text(KIT_FIGURE_KICKER, KICKER)
    title = text_of(spec.head.title)
    if title:
        writer.text(title, FIGURE_TITLE)
    draw_still(writer, diagram_still(spec), max_height=KIT_STILL_MM)
    for line in kit_diagram_lines(spec, shown):
        if line is not None:
            writer.text(line.plain, NOTE if line.role == "note" else CELL)
    caption = text_of(spec.head.caption)
    if caption:
        writer.text(caption, NOTE)
    writer.go_to(writer.y + FIGURE_GAP_MM)


def timeline_places_pdf(writer: PdfWriter, block: TimelineMapBlock) -> None:
    placed = [
        (index, place)
        for index, place in enumerate(block.places)
        if place.longitude is not None and place.latitude is not None
    ]
    if not placed:
        return
    pins = [MapPin(place.longitude or 0.0, place.latitude or 0.0, index + 1) for index, place in placed]
    at = {index: position for position, (index, _) in enumerate(placed)}
    routes = [
        (at[route.start], at[route.end]) for route in block.routes if route.start in at and route.end in at
    ]
    districts = [place.district_lgd for _, place in placed if place.district_lgd is not None]
    if not draw_still(
        writer, timeline_still(MapAsk(pins=pins, routes=routes, districts=districts, homes=[]))
    ):
        return
    named = "; ".join(f"{index + 1} {place.name}" for index, place in placed)
    writer.text(f"{PLACES_LABEL}: {named}", NOTE)
