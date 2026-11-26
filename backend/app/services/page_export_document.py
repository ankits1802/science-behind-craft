from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any

from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.research.component_specs import checked_spec
from app.research.monograph_document import MonographDocument
from app.research.monograph_page import ComponentEntry, MonographContent
from app.research.translation_passages import NAME_UNITS
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS

from .monograph_document import component_specs, has_authored_content
from .page_export_coded import coded_figure_figure
from .page_export_figures import FigureAsk, PaperPage, generic_figure
from .page_export_kit import kit_diagram_figure, label_card_figure, swatch_cards_figure, timeline_map_figure
from .page_export_labs import choice_toggle_figure, experiment_lab_figure
from .page_export_model import ExportBlock, ExportChapter, ExportFigure, ExportText, PageExport
from .page_export_pictures import NO_PICTURES, PagePictures
from .page_export_plates import picture_plate_figure, specimen_plate_figure
from .page_export_science import (
    dip_player_figure,
    molecule_figure,
    reaction_player_figure,
    stage_player_figure,
)
from .page_export_units import PageTexts, page_references
from .page_export_words import READING, ExportWords, export_words

__all__ = ["FIGURES", "component_figure", "export_specs", "page_export"]

logger = logging.getLogger(__name__)

FigureBuilder = Callable[[FigureAsk, object], ExportFigure | None]
FIGURES: Mapping[str, FigureBuilder] = MappingProxyType(
    {
        "picture_plate": picture_plate_figure,
        "specimen_plate": specimen_plate_figure,
        "diagram": kit_diagram_figure,
        "timeline_map": timeline_map_figure,
        "swatch_cards": swatch_cards_figure,
        "label_card": label_card_figure,
        "reaction_player": reaction_player_figure,
        "dip_player": dip_player_figure,
        "stage_player": stage_player_figure,
        "molecule_3d": molecule_figure,
        "experiment_lab": experiment_lab_figure,
        "choice_toggle": choice_toggle_figure,
        "coded_figure": coded_figure_figure,
    }
)


def export_specs(document: MonographDocument) -> dict[str, dict[str, Any]]:
    authored = component_specs(document.content) if has_authored_content(document.subject_slug) else {}
    return {**authored, **document.specs}


def page_export(
    document: MonographDocument,
    specs: Mapping[str, Mapping[str, Any]],
    *,
    pictures: PagePictures = NO_PICTURES,
    words: ExportWords | None = None,
) -> PageExport:
    content = document.content
    page = PaperPage(PageTexts(content), words or export_words(document.language), pictures)
    chapters = _chapter_blocks(content, specs, page)
    titles = {chapter.key: chapter.title for chapter in content.chapters}
    return PageExport(
        title=document.title,
        language=document.language,
        page_url=document.page_url,
        version=document.version,
        reading_note=_reading_note(document, page.words),
        chapters=tuple(
            ExportChapter(key, titles.get(key), tuple(blocks)) for key, blocks in chapters.items() if blocks
        ),
        references=page_references(content),
        words=page.words,
    )


def _chapter_blocks(
    content: MonographContent, specs: Mapping[str, Mapping[str, Any]], page: PaperPage
) -> dict[str, list[ExportBlock]]:
    texts = page.texts
    within = _within(content)
    entries = {entry.label: entry for entry in content.components}
    chapters: dict[str, list[ExportBlock]] = {}
    drawn: set[str] = set()

    def figure(label: str) -> ExportFigure:
        drawn.add(label)
        return component_figure(entries[label], specs.get(label), within.get(label, ()), page)

    for placed in content.layout:
        blocks = chapters.setdefault(placed.chapter, [])
        if placed.kind == "component" and placed.ref in entries and placed.ref not in drawn:
            blocks.append(figure(placed.ref))
        elif placed.kind == "unit" and placed.within is None and placed.ref not in NAME_UNITS:
            text = texts.unit(placed.ref)
            if text is not None:
                blocks.append(text)
    for entry in content.components:
        if entry.label not in drawn:
            chapters.setdefault(entry.chapter, []).append(figure(entry.label))
    return chapters


def component_figure(
    entry: ComponentEntry, spec: Mapping[str, Any] | None, within: tuple[str, ...], page: PaperPage
) -> ExportFigure:
    ask = FigureAsk(entry=entry, spec=spec, within=within, page=page)
    builder = FIGURES.get(entry.kind)
    model = _model(entry, spec) if builder is not None else None
    figure = builder(ask, model) if builder is not None and model is not None else None
    return figure if figure is not None else generic_figure(ask)


def _model(entry: ComponentEntry, spec: Mapping[str, Any] | None) -> object | None:
    if spec is None:
        return None
    try:
        return checked_spec(entry.kind, spec)
    except (InvalidInput, ValidationError) as problem:
        logger.warning(
            "the export draws %s from its words alone: its spec does not parse: %s", entry.label, problem
        )
        return None


def _within(content: MonographContent) -> dict[str, tuple[str, ...]]:
    held: dict[str, list[str]] = {}
    for placed in content.layout:
        if placed.within is not None and placed.kind == "unit":
            held.setdefault(placed.within, []).append(placed.ref)
    return {label: tuple(refs) for label, refs in held.items()}


def _reading_note(document: MonographDocument, words: ExportWords) -> ExportText | None:
    translation = document.translation
    if translation is None or document.language not in ANSWER_LANGUAGE_SPECS:
        return None
    label = ANSWER_LANGUAGE_SPECS[document.language].label
    return words.text(READING, translated=translation.translated, passages=translation.passages, label=label)
