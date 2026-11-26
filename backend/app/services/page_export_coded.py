from __future__ import annotations

from dataclasses import replace

from app.research.coded_figure_still import code_still, still_node, worded_still
from app.research.component_specs_science_coded import CodedFigureSpec

from .export_still_svg import svg_still
from .page_export_figures import FigureAsk
from .page_export_model import ExportFigure, ExportPicture
from .page_export_pictures import clip_still_src

__all__ = ["coded_figure_figure"]


def coded_figure_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, CodedFigureSpec):
        return None
    markup = spec.still or code_still(spec.code)
    words = {text.key: ask.texts.plain(text.unit) for text in spec.texts}
    still = svg_still(worded_still(still_node(markup), words)) if markup is not None else None
    lines = [
        ask.unit(spec.alt),
        *ask.units(text.unit for text in spec.texts),
        *ask.units(value.reading for value in spec.values),
    ]
    clips = [film for film in spec.films if film.clip is not None]
    credits = [film.credit for film in clips if film.credit]
    figure = ask.figure([still], lines, ask.title(spec.head.title), credits=credits)
    stills = [ask.pictures.of(clip_still_src(film.clip)) for film in clips if film.clip is not None]
    alt = ask.texts.plain(spec.alt)
    pictures = tuple(ExportPicture(found, alt) for found in stills if found is not None)
    return replace(figure, pictures=pictures) if pictures else figure
