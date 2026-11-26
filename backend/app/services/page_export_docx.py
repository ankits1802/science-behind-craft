from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.research.vocabulary import ANSWER_LANGUAGE_SPECS, RIGHT_TO_LEFT_SCRIPTS

from .docx_parts import DocColours
from .docx_writer import JPEG, DocRun, DocxWriter
from .export_still_png import STILL_PIXELS, still_png
from .export_stills import Colour, Still, ink, token_colour
from .page_export_model import ExportFigure, ExportPicture, ExportText, PageExport, Role
from .page_export_pdf import page_meta
from .page_export_words import SOURCES, kind_word

__all__ = ["FIGURE_ROLE_STYLES", "ROLE_STYLES", "STILL_WIDTH_MM", "page_docx"]

STILL_WIDTH_MM = 150.0
STILL_HEIGHT_MM = 110.0
INDIGO = "--indigo"
ROLE_STYLES: Mapping[Role, str] = MappingProxyType(
    {
        "heading": "Heading2",
        "subheading": "Heading3",
        "body": "Normal",
        "term": "Term",
        "item": "ListItem",
        "quote": "Quote",
        "note": "Note",
        "credit": "Credit",
    }
)
FIGURE_ROLE_STYLES: Mapping[Role, str] = MappingProxyType(
    {
        "heading": "CaptionItem",
        "subheading": "CaptionItem",
        "body": "Caption",
        "term": "CaptionItem",
        "item": "CaptionItem",
        "quote": "Caption",
        "note": "Note",
        "credit": "Credit",
    }
)


def page_docx(export: PageExport) -> bytes:
    script = (
        ANSWER_LANGUAGE_SPECS[export.language].script if export.language in ANSWER_LANGUAGE_SPECS else None
    )
    writer = DocxWriter(
        title=export.title,
        language=export.language,
        colours=_colours(),
        right_to_left=script in RIGHT_TO_LEFT_SCRIPTS,
    )
    writer.paragraph([DocRun(export.title)], "Title")
    writer.paragraph([DocRun(page_meta(export))], "Meta")
    if export.reading_note:
        _text(writer, export.reading_note, ROLE_STYLES)
    for chapter in export.chapters:
        if chapter.title:
            writer.paragraph([DocRun(chapter.title)], "Heading1")
        for block in chapter.blocks:
            if isinstance(block, ExportFigure):
                _figure(writer, block, export)
            else:
                _text(writer, block, ROLE_STYLES)
    words = export.words
    writer.paragraph([DocRun(words.said(SOURCES), lang=words.lang(SOURCES))], "Heading1")
    for reference in export.references:
        runs = [DocRun(f"[{reference.number}] "), DocRun(reference.text)]
        writer.paragraph(runs, "Reference", link=reference.url)
    return writer.output()


def doc_runs(text: ExportText) -> list[DocRun]:
    return [DocRun(run.text, run.style, run.lang or text.lang) for run in text.runs]


def _text(writer: DocxWriter, text: ExportText, styles: Mapping[Role, str]) -> None:
    if text.plain.strip():
        writer.paragraph(doc_runs(text), styles[text.role])


def _figure(writer: DocxWriter, figure: ExportFigure, export: PageExport) -> None:
    kicker = kind_word(figure.kind)
    writer.paragraph([DocRun(export.words.said(kicker), lang=export.words.lang(kicker))], "Kicker")
    writer.paragraph([DocRun(figure.title)], "FigureTitle")
    for still in figure.stills:
        _still(writer, still, figure.title)
    for shown in figure.pictures:
        _picture(writer, shown)
    for line in figure.lines:
        _text(writer, line, FIGURE_ROLE_STYLES)
    if figure.note:
        writer.paragraph([DocRun(figure.note, lang=figure.note_lang)], "Note")
    for credit in figure.credits:
        writer.paragraph([DocRun(credit)], "Credit")


def _picture(writer: DocxWriter, shown: ExportPicture) -> None:
    picture = shown.picture
    width = min(STILL_WIDTH_MM, STILL_HEIGHT_MM * picture.width / max(picture.height, 1))
    size = (picture.width, picture.height)
    writer.picture(picture.data, size, description=shown.alt, width_mm=width, extension=JPEG)


def _still(writer: DocxWriter, still: Still, description: str) -> None:
    picture = still_png(still, pixels=still.pixels or STILL_PIXELS)
    if picture is None:
        return
    width = min(STILL_WIDTH_MM, STILL_HEIGHT_MM * picture.width / max(picture.height, 1))
    writer.picture(picture.data, (picture.width, picture.height), description=description, width_mm=width)


def _colours() -> DocColours:
    return DocColours(heading=_hex(token_colour(INDIGO) or ink(1)), body=_hex(ink(1)), soft=_hex(ink(2)))


def _hex(colour: Colour) -> str:
    return "".join(f"{channel:02X}" for channel in colour)
