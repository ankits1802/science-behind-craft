from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import islice
from types import MappingProxyType
from typing import Any

from app.research.datasets import DatasetRef
from app.research.export_text import CREDIT_SEPARATOR
from app.research.monograph_page import ComponentEntry
from app.research.spec_strings import spec_strings

from .export_still_kit import kit_scene_parts, scene_still
from .export_still_svg import svg_still
from .export_stills import Still
from .page_export_model import ExportFigure, ExportText, Role, Run, plain_text
from .page_export_units import PageTexts

__all__ = [
    "DRAWINGS_MAX",
    "PAPER_NOTES",
    "FigureAsk",
    "dataset_credit",
    "drawn_stills",
    "generic_figure",
    "picture_lines",
    "prefixed",
    "scene_of",
]

DRAWINGS_MAX = 4
SVG_TAG = "svg"
PLAYS = "This part plays or answers on the page; its words are given here."
PAPER_NOTES: Mapping[str, str] = MappingProxyType(
    {
        "reaction_player": (
            "On the page the reader steps through each reaction and scrubs between them; here every step is "
            "listed and the drawing rests on the step the page opens on."
        ),
        "dip_player": (
            "On the page the reader dips again and watches each dip deepen the colour; here the dips are listed "
            "in order and the drawing rests as the page opens."
        ),
        "stage_player": "On the page the stages play one after another; here they are listed in order.",
        "molecule_3d": "On the page the reader turns and zooms the model; here it is drawn as it rests.",
        "timeline_map": (
            "On the page the map moves through the years and each pin opens its entry; here it rests on its last "
            "year with every place pinned and numbered."
        ),
        "experiment_lab": "On the page the reader chooses an experiment; here every choice is listed.",
        "choice_toggle": "On the page the reader switches between the choices; here every choice is shown.",
        "map_sequence": "On the page the maps step one after another; here each is listed in order.",
        "process_replay": PLAYS,
        "quiz": PLAYS,
        "ask_next": PLAYS,
        "generator": PLAYS,
        "audio_player": PLAYS,
        "voice": PLAYS,
        "film": PLAYS,
        "ai_video": PLAYS,
        "model_explainer": PLAYS,
        "explainer": PLAYS,
        "reading_level": PLAYS,
        "language_switch": PLAYS,
        "citation_tool": PLAYS,
    }
)


@dataclass
class FigureAsk:
    entry: ComponentEntry
    spec: Mapping[str, Any] | None
    within: tuple[str, ...]
    texts: PageTexts
    used: set[str] = field(default_factory=set)

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
        return ExportFigure(
            label=self.entry.label,
            kind=self.entry.kind,
            title=title or self.entry.title,
            stills=tuple(still for still in stills if still is not None and still.drawn),
            lines=(*shown, *self.leftover()),
            note=PAPER_NOTES.get(self.entry.kind),
            credits=tuple(dict.fromkeys(credits)),
        )


def generic_figure(ask: FigureAsk) -> ExportFigure:
    spec = ask.spec or {}
    return ask.figure(drawn_stills(spec), picture_lines(spec))


def prefixed(prefix: str, text: ExportText | None, role: Role = "item") -> ExportText:
    if text is None:
        return plain_text(prefix.rstrip(": ").strip(), role)
    return ExportText(runs=(Run(prefix), *text.runs), role=role, lang=text.lang)


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


def picture_lines(spec: Mapping[str, Any]) -> Iterator[ExportText]:
    for node in _nodes(spec):
        if isinstance(node.get("src"), str) and isinstance(node.get("alt"), str) and node["alt"].strip():
            yield plain_text(f"Picture: {node['alt'].strip()}", "note")


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
