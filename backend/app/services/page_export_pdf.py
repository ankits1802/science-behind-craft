from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from types import MappingProxyType

from app.research.export_text import CREDIT_SEPARATOR
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS

from .export_pdf_still import draw_still
from .export_pdf_text import sentence_case
from .export_stills import ink, token_colour
from .page_export_model import ExportFigure, ExportText, PageExport, Role
from .pdf_writer import PdfWriter, TextStyle

__all__ = ["FIGURE_STILL_MM", "KIND_LABELS", "SOURCES_HEADING", "kind_label", "page_meta", "page_pdf"]

SOURCES_HEADING = "Sources"
FIGURE_STILL_MM = 80.0
VERSION_MARK = "v{version}"
INDIGO = "--indigo"
KIND_LABELS: Mapping[str, str] = MappingProxyType({"molecule_3d": "Molecule in 3D"})


@dataclass(frozen=True)
class _Styles:
    title: TextStyle
    meta: TextStyle
    chapter: TextStyle
    kicker: TextStyle
    figure: TextStyle
    roles: Mapping[Role, TextStyle]
    figure_roles: Mapping[Role, TextStyle]
    reference: TextStyle


@cache
def _styles() -> _Styles:
    heading = token_colour(INDIGO) or ink(1)
    body, soft, faint = ink(1), ink(2), ink(3)
    note = TextStyle(size=8.5, colour=soft, gap_after=1.5)
    credit = TextStyle(size=7.5, colour=faint, gap_after=1)
    roles: dict[Role, TextStyle] = {
        "heading": TextStyle(size=14, bold=True, colour=heading, gap_after=2.5),
        "subheading": TextStyle(size=11.5, bold=True, colour=body, gap_after=1.5),
        "body": TextStyle(size=10.5, colour=body, gap_after=2),
        "term": TextStyle(size=10.5, bold=True, colour=body, gap_after=0.5),
        "item": TextStyle(size=10.5, colour=body, gap_after=1.5),
        "quote": TextStyle(size=10.5, colour=soft, gap_after=2),
        "note": note,
        "credit": credit,
    }
    figure_roles: dict[Role, TextStyle] = {
        **{role: TextStyle(size=9, colour=body, gap_after=1) for role in roles},
        "item": TextStyle(size=9, bold=True, colour=body, gap_after=0.8),
        "subheading": TextStyle(size=9, bold=True, colour=body, gap_after=0.8),
        "note": TextStyle(size=8, colour=soft, gap_after=1),
        "credit": credit,
    }
    return _Styles(
        title=TextStyle(size=24, bold=True, colour=body, gap_after=3),
        meta=TextStyle(size=9.5, colour=soft, gap_after=5),
        chapter=TextStyle(size=17, bold=True, colour=heading, gap_after=3),
        kicker=TextStyle(size=8, bold=True, colour=heading, gap_after=0.8),
        figure=TextStyle(size=11, bold=True, colour=body, gap_after=2),
        roles=roles,
        figure_roles=figure_roles,
        reference=TextStyle(size=8.5, colour=body, gap_after=1.2),
    )


def page_pdf(export: PageExport) -> bytes:
    styles = _styles()
    writer = PdfWriter(export.language, orientation="portrait", title=export.title)
    writer.new_page()
    writer.text(export.title, styles.title)
    writer.text(page_meta(export), styles.meta)
    if export.reading_note:
        writer.text(export.reading_note, styles.roles["note"])
    for chapter in export.chapters:
        if chapter.title:
            writer.text(chapter.title, styles.chapter)
        for block in chapter.blocks:
            if isinstance(block, ExportFigure):
                _figure(writer, block, styles)
            else:
                _text(writer, block, styles.roles)
    writer.text(SOURCES_HEADING, styles.chapter)
    for reference in export.references:
        writer.item(f"[{reference.number}]", reference.text, styles.reference, link=reference.url)
    return writer.output()


def kind_label(kind: str) -> str:
    return KIND_LABELS.get(kind) or sentence_case(kind)


def page_meta(export: PageExport) -> str:
    language = (
        ANSWER_LANGUAGE_SPECS[export.language].label if export.language in ANSWER_LANGUAGE_SPECS else None
    )
    parts = (export.page_url, VERSION_MARK.format(version=export.version), language)
    return CREDIT_SEPARATOR.join(part for part in parts if part)


def _text(writer: PdfWriter, text: ExportText, roles: Mapping[Role, TextStyle]) -> None:
    shown = text.plain.strip()
    if shown:
        writer.text(shown, roles[text.role])


def _figure(writer: PdfWriter, figure: ExportFigure, styles: _Styles) -> None:
    writer.text(kind_label(figure.kind), styles.kicker)
    writer.text(figure.title, styles.figure)
    for still in figure.stills:
        draw_still(writer, still, max_height=FIGURE_STILL_MM)
    for line in figure.lines:
        _text(writer, line, styles.figure_roles)
    if figure.note:
        writer.text(figure.note, styles.figure_roles["note"])
    for credit in figure.credits:
        writer.text(credit, styles.figure_roles["credit"])
    writer.go_to(writer.y + 2)
