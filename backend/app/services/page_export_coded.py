from __future__ import annotations

import re

from app.geo.map_base import BaseAsk, SiteBox
from app.research.coded_figure_still import code_still, still_node, worded_still
from app.research.component_specs_science_coded import CodedFigureSpec, CodedMap
from app.research.datasets import BOUNDARY_CAPTION

from .export_map_base import base_datasets, on_base
from .export_still_paint import numbers
from .export_still_svg import svg_still
from .page_export_figures import FigureAsk, dataset_credit
from .page_export_model import ExportFigure, ExportText, plain_text

__all__ = ["DATA_MAP", "coded_figure_figure", "coded_map_box"]

DATA_MAP = re.compile(r"^<svg\s[^>]*\bdata-map(?=[\s=/>])")
VIEW_BOX = "viewBox"


def coded_figure_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, CodedFigureSpec):
        return None
    markup = spec.still or code_still(spec.code)
    words = {text.key: ask.texts.plain(text.unit) for text in spec.texts}
    still = svg_still(worded_still(still_node(markup), words)) if markup is not None else None
    lines: list[ExportText | None] = [
        ask.unit(spec.alt),
        *ask.units(text.unit for text in spec.texts),
        *ask.units(value.reading for value in spec.values),
    ]
    box = coded_map_box(markup) if spec.map is not None else None
    if still is None or box is None or spec.map is None:
        return ask.figure([still], lines, ask.title(spec.head.title))
    base = _base_ask(spec.map)
    credits = [dataset_credit(dataset) for dataset in base_datasets(box, base)]
    lines.append(plain_text(BOUNDARY_CAPTION, "credit"))
    return ask.figure([on_base(still, box, base)], lines, ask.title(spec.head.title), credits)


def coded_map_box(markup: str | None) -> SiteBox | None:
    if markup is None or not DATA_MAP.match(markup.lstrip()):
        return None
    box = numbers(str(still_node(markup)["attrs"].get(VIEW_BOX, "")))
    if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
        return None
    return SiteBox(box[0], box[1], box[2], box[3])


def _base_ask(coded: CodedMap) -> BaseAsk:
    layers = set(coded.layers)
    return BaseAsk(
        relief="relief" in layers,
        rivers="rivers" in layers,
        districts="districts" in layers,
        homes=tuple(coded.districts),
    )
