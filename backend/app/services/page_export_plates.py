from __future__ import annotations

from dataclasses import replace

from app.research.component_specs_plates import PicturePlateSpec, SpecimenPlateSpec

from .page_export_figures import FigureAsk
from .page_export_model import ExportFigure, ExportPicture, ExportText
from .page_export_pictures import copyable, plate_picture
from .page_export_words import PICTURE, PICTURE_CLOSED, PICTURE_UNREAD, ExportWord

__all__ = ["picture_plate_figure", "specimen_plate_figure"]

Plate = PicturePlateSpec | SpecimenPlateSpec


def picture_plate_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, PicturePlateSpec):
        return None
    captions = [caption.unit for caption in spec.figure.captions] if spec.figure is not None else []
    return _plate_figure(ask, spec, ask.units(captions, "body"))


def specimen_plate_figure(ask: FigureAsk, spec: object) -> ExportFigure | None:
    if not isinstance(spec, SpecimenPlateSpec):
        return None
    lines = [ask.unit(spec.kicker, "note"), ask.unit(spec.name, "subheading"), ask.unit(spec.sentence)]
    return _plate_figure(ask, spec, [line for line in lines if line is not None])


def _plate_figure(ask: FigureAsk, spec: Plate, lines: list[ExportText]) -> ExportFigure:
    shown = plate_picture(spec)
    credit = ask.plain(shown.credit) if shown is not None else ""
    credits = [credit] if credit else []
    if not copyable(credit):
        return _described(ask, spec, (lines, credits), PICTURE_CLOSED)
    picture = ask.pictures.of(spec.picture.src)
    if picture is None:
        return _described(ask, spec, (lines, credits), PICTURE_UNREAD)
    figure = ask.figure([], lines, credits=credits)
    return replace(figure, pictures=(ExportPicture(picture, spec.picture.alt),))


def _described(
    ask: FigureAsk, spec: Plate, parts: tuple[list[ExportText], list[str]], why: ExportWord
) -> ExportFigure:
    lines, credits = parts
    described = ask.words.labelled(PICTURE, spec.picture.alt.strip())
    figure = ask.figure([], [*lines, described], credits=credits)
    return replace(figure, note=ask.words.said(why), note_lang=ask.words.lang(why))
