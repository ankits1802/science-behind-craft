from __future__ import annotations

import re
from dataclasses import replace

from app.geo.map_base import BaseAsk, SiteBox
from app.geo.map_waters import WaterAsk
from app.research.coded_figure_still import code_still, still_node, worded_still
from app.research.component_specs_science_coded import CodedFigureSpec, CodedFilm, CodedMap
from app.research.datasets import BOUNDARY_CAPTION

from .export_map_base import on_base, paper_base
from .export_still_paint import numbers
from .export_still_svg import svg_still
from .page_export_figures import FigureAsk, dataset_credit
from .page_export_model import ExportFigure, ExportPicture, ExportText, plain_text
from .page_export_pictures import clip_still_src

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
    clips = [film for film in spec.films if film.clip is not None]
    credits = [film.credit for film in clips if film.credit]
    box = coded_map_box(markup) if spec.map is not None else None
    if still is not None and box is not None and spec.map is not None:
        paper = paper_base(box, _base_ask(spec.map), _water_ask(spec.map))
        credits = [*(dataset_credit(dataset) for dataset in paper.datasets), *credits]
        lines.append(plain_text(BOUNDARY_CAPTION, "credit"))
        still = on_base(still, paper)
    figure = ask.figure([still], lines, ask.title(spec.head.title), credits)
    return _with_clip_stills(ask, spec, clips, figure)


def _with_clip_stills(
    ask: FigureAsk, spec: CodedFigureSpec, clips: list[CodedFilm], figure: ExportFigure
) -> ExportFigure:
    stills = [ask.pictures.of(clip_still_src(film.clip)) for film in clips if film.clip is not None]
    alt = ask.texts.plain(spec.alt)
    pictures = tuple(ExportPicture(found, alt) for found in stills if found is not None)
    return replace(figure, pictures=pictures) if pictures else figure


def coded_map_box(markup: str | None) -> SiteBox | None:
    if markup is None or not DATA_MAP.match(markup.lstrip()):
        return None
    box = numbers(str(still_node(markup)["attrs"].get(VIEW_BOX, "")))
    if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
        return None
    return SiteBox(box[0], box[1], box[2], box[3])


def _water_ask(coded: CodedMap) -> WaterAsk:
    return WaterAsk(rivers=tuple(coded.rivers), dams=tuple(coded.dams), plain="rivers" in coded.layers)


def _base_ask(coded: CodedMap) -> BaseAsk:
    layers = set(coded.layers)
    return BaseAsk(
        relief="relief" in layers,
        rivers="rivers" in layers,
        districts="districts" in layers,
        homes=tuple(coded.districts),
    )
