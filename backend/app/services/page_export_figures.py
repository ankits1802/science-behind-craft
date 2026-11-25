from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import islice
from typing import Any

from app.research.datasets import DatasetRef
from app.research.export_text import CREDIT_SEPARATOR
from app.research.monograph_page import ComponentEntry
from app.research.spec_strings import spec_strings

from .export_still_kit import kit_scene_parts, scene_still
from .export_still_svg import svg_still
from .export_stills import Still
from .page_export_model import ExportFigure, ExportText, Role, Run
from .page_export_pictures import NO_PICTURES, PagePictures
from .page_export_units import PageTexts
from .page_export_words import ENGLISH_EXPORT_WORDS, PAPER_NOTES, PICTURE, ExportWords, paper_note

__all__ = [
    "DRAWINGS_MAX",
    "PAPER_NOTES",
    "FigureAsk",
    "PaperPage",
    "dataset_credit",
    "drawn_stills",
    "generic_figure",
    "picture_lines",
    "prefixed",
    "scene_of",
]

DRAWINGS_MAX = 4
SVG_TAG = "svg"


@dataclass(frozen=True)
class PaperPage:
    texts: PageTexts
    words: ExportWords = ENGLISH_EXPORT_WORDS
    pictures: PagePictures = NO_PICTURES


@dataclass
class FigureAsk:
    entry: ComponentEntry
    spec: Mapping[str, Any] | None
    within: tuple[str, ...]
    page: PaperPage
    used: set[str] = field(default_factory=set)

    @property
    def texts(self) -> PageTexts:
        return self.page.texts

    @property
    def words(self) -> ExportWords:
        return self.page.words

    @property
    def pictures(self) -> PagePictures:
        return self.page.pictures

    def unit(self, ref: str | None, role: Role | None = None) -> ExportText | None:
        if ref:
            self.used.add(ref)
        return self.texts.unit(ref, role)

    def units(self, refs: Iterable[str | None], role: Role | None = None) -> list[ExportText]:
        found = (self.unit(ref, role) for ref in dict.fromkeys(refs))
        return [text for text in found if text is not None]

    def plain(self, ref: str | None) -> str:
        text = self.unit(ref)
        return text.plain.strip() if text is not None else ""

    def title(self, ref: str | None) -> str:
        return self.plain(ref) or self.entry.title

    def replaced(self, *refs: str | None) -> None:
        self.used.update(ref for ref in refs if ref)

    def leftover(self) -> list[ExportText]:
        held = self.within or tuple(self.spec_refs())
        return self.units(ref for ref in held if ref not in self.used)

    def spec_refs(self) -> list[str]:
        units = self.texts.content.units
        return list(dict.fromkeys(value for value in spec_strings(self.spec or {}) if value in units))

    def figure(
        self,
        stills: Iterable[Still | None],
        lines: Iterable[ExportText | None],
        title: str | None = None,
        credits: Iterable[str] = (),
    ) -> ExportFigure:
        shown = [line for line in lines if line is not None]
        note = PAPER_NOTES.get(self.entry.kind)
        word = paper_note(note) if note is not None else None
        return ExportFigure(
            label=self.entry.label,
            kind=self.entry.kind,
            title=title or self.entry.title,
            stills=tuple(still for still in stills if still is not None and still.drawn),
            lines=(*shown, *self.leftover()),
            note=self.words.said(word) if word is not None else None,
            credits=tuple(dict.fromkeys(credits)),
            note_lang=self.words.lang(word) if word is not None else None,
        )


def generic_figure(ask: FigureAsk) -> ExportFigure:
    spec = ask.spec or {}
    return ask.figure(drawn_stills(spec), picture_lines(spec, ask.words))


def prefixed(prefix: str | Run, text: ExportText | None, role: Role = "item") -> ExportText:
    head = prefix if isinstance(prefix, Run) else Run(prefix)
    if text is None:
        return ExportText(
            runs=(Run(head.text.rstrip(": ").strip(), lang=head.lang),), role=role, lang=head.lang
        )
    return ExportText(runs=(head, *text.runs), role=role, lang=text.lang)


def scene_of(value: Any) -> Still | None:
    parts = kit_scene_parts(value)
    if parts is not None:
        return scene_still(parts)
    if isinstance(value, Mapping) and value.get("tag"):
        return svg_still(value)
    if isinstance(value, list) and value:
        return svg_still({"tag": "g", "children": value})
    return None


def drawn_stills(spec: Mapping[str, Any]) -> tuple[Still, ...]:
    stills = (svg_still(node) for node in _drawings(spec))
    return tuple(islice((still for still in stills if still.drawn), DRAWINGS_MAX))


def picture_lines(spec: Mapping[str, Any], words: ExportWords = ENGLISH_EXPORT_WORDS) -> Iterator[ExportText]:
    for node in _nodes(spec):
        if isinstance(node.get("src"), str) and isinstance(node.get("alt"), str) and node["alt"].strip():
            yield words.labelled(PICTURE, node["alt"].strip())


def dataset_credit(dataset: DatasetRef) -> str:
    parts = (dataset.title, dataset.edition, dataset.period, dataset.native_resolution, dataset.licence)
    return CREDIT_SEPARATOR.join(parts)


def _drawings(value: Any) -> Iterator[Mapping[str, Any]]:
    for node in _nodes(value):
        if node.get("tag") == SVG_TAG:
            yield node


def _nodes(value: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        if value.get("tag") == SVG_TAG:
            return
        for item in value.values():
            yield from _nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _nodes(item)
