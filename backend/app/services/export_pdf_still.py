from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from .export_stills import Affine, Still, StillText, scaled, translated
from .pdf_writer import Box, PdfWriter, TextAlign, TextStyle

__all__ = ["MM_PER_POINT", "STILL_GAP_MM", "STILL_MAX_MM", "draw_still"]

MM_PER_POINT = 25.4 / 72
STILL_MAX_MM = 90.0
STILL_GAP_MM = 2.0
TEXT_MIN_POINTS = 6.0
LABEL_WIDTH_MM = 40.0
BASELINE_SHARE = 0.75
ALIGNS: Mapping[str, TextAlign] = MappingProxyType({"start": "L", "middle": "C", "end": "R"})


def draw_still(writer: PdfWriter, still: Still, *, max_height: float = STILL_MAX_MM) -> bool:
    if not still.drawn or still.width <= 0 or still.height <= 0:
        return False
    scale = min(writer.width / still.width, max_height / still.height)
    width, height = still.width * scale, still.height * scale
    top = writer.room(height)
    affine = scaled(scale).then(translated(writer.left + (writer.width - width) / 2, top))
    for path in still.paths:
        points = [affine.apply(point) for point in path.points]
        if path.fill is not None and len(points) > 2:
            writer.shape(points, fill=path.fill)
        if path.line is not None:
            closed = [*points, points[0]] if path.closed else points
            writer.stroke(closed, path.line, width=max(path.width * scale, 0.05))
    for text in still.texts:
        _label(writer, text, affine)
    writer.go_to(top + height + STILL_GAP_MM)
    return True


def _label(writer: PdfWriter, text: StillText, affine: Affine) -> None:
    x, y = affine.apply(text.at)
    points = max(text.size * affine.scale / MM_PER_POINT, TEXT_MIN_POINTS)
    height = points * MM_PER_POINT
    align = ALIGNS[text.anchor]
    left = {"L": x, "C": x - LABEL_WIDTH_MM / 2, "R": x - LABEL_WIDTH_MM}[align]
    box = Box(left, y - height * BASELINE_SHARE, LABEL_WIDTH_MM, height)
    writer.label(text.text, TextStyle(size=points, colour=text.colour, gap_after=0), box, align=align)
