from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.models.component_kinds import LINK_TOOL_KINDS

from .monograph_document import MonographDocument
from .monograph_page import ComponentEntry
from .spec_strings import spec_strings

__all__ = ["OPENING", "PICTURE_KIND", "ReadPage", "Sentence", "cite_keys", "node_text"]

OPENING = "opening"
PICTURE_KIND = "picture_plate"
SENTENCE_TAG = "p"
CITE_MARK = "cite"


@dataclass(frozen=True)
class Sentence:
    unit_id: str
    text: str
    field: str | None
    chapter: str
    claim_ids: tuple[str, ...]


def node_text(nodes: Sequence[Any]) -> str:
    return "".join(
        node if isinstance(node, str) else node_text(node.get("c", []))
        for node in nodes
        if isinstance(node, str | dict)
    )


@dataclass(frozen=True)
class ReadPage:
    document: MonographDocument
    sentences: tuple[Sentence, ...]
    within: Mapping[str, str]
    figures: tuple[ComponentEntry, ...]
    pictures: tuple[ComponentEntry, ...]

    @classmethod
    def of(cls, document: MonographDocument) -> ReadPage:
        content = document.content
        within = {entry.ref: entry.within for entry in content.layout if entry.within is not None}
        placed = [entry.ref for entry in content.layout if entry.kind == "unit" and entry.within is None]
        sentences = tuple(
            Sentence(ref, node_text(unit.nodes).strip(), unit.field, unit.chapter, tuple(unit.claim_ids))
            for ref in placed
            if (unit := content.units.get(ref)) is not None and unit.tag == SENTENCE_TAG and unit.claim_ids
        )
        figures = tuple(c for c in content.components if c.kind not in (PICTURE_KIND, *LINK_TOOL_KINDS))
        pictures = tuple(c for c in content.components if c.kind == PICTURE_KIND)
        return cls(document, sentences, within, figures, pictures)

    def text(self, unit_id: str) -> str:
        unit = self.document.content.units.get(unit_id)
        return "" if unit is None else node_text(unit.nodes).strip()

    def held(self, label: str) -> list[str]:
        return [unit for unit, owner in self.within.items() if owner == label]

    def named(self, label: str) -> list[str]:
        units = self.document.content.units
        spec = self.document.specs.get(label, {})
        return list(dict.fromkeys([*self.held(label), *(ref for ref in spec_strings(spec) if ref in units)]))

    def cited(self, label: str) -> bool:
        content = self.document.content
        spec = self.document.specs.get(label, {})
        named = self.named(label)
        marks = [
            *cite_keys(spec),
            *(key for ref in named if ref in content.units for key in cite_keys(content.units[ref].nodes)),
        ]
        return (
            any(ref in content.citations for ref in named)
            or any(key in content.citations for key in marks)
            or bool(spec.get("sources"))
            or label in self.document.fragments
        )

    def plate(self, label: str) -> tuple[str, str, str]:
        spec = self.document.specs.get(label, {})
        figure = spec.get("figure") or {}
        captions = [
            self.text(str(c.get("unit"))) for c in figure.get("captions") or [] if isinstance(c, dict)
        ]
        credit = self.text(str(figure.get("credit"))) if figure.get("credit") else ""
        return str((spec.get("picture") or {}).get("src") or ""), " ".join(captions), credit

    def lede(self) -> list[Sentence]:
        return [sentence for sentence in self.sentences if sentence.chapter == OPENING]

    def by_field(self) -> Counter[str]:
        return Counter(sentence.field for sentence in self.sentences if sentence.field)


def cite_keys(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        own = [str(value["key"])] if value.get("m") == CITE_MARK and "key" in value else []
        return [*own, *(key for item in value.values() for key in cite_keys(item))]
    if isinstance(value, list):
        return [key for item in value for key in cite_keys(item)]
    return []
