from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from app.research.component_specs_science_parts import Styled
from app.research.export_text import CREDIT_SEPARATOR, marker
from app.research.monograph_page import CitedSource, MonographContent

from .page_export_model import ExportReference, ExportText, Role, Run, RunStyle

__all__ = ["CITE_MARK", "TAG_ROLES", "PageTexts", "page_references", "rich_runs"]

CITE_MARK = "cite"
MARK = "m"
CHILDREN = "c"
SOURCES = "g"
MARK_STYLES: Mapping[str, RunStyle] = MappingProxyType({"i": "i", "b": "b", "sub": "sub", "sup": "sup"})
TAG_ROLES: Mapping[str, Role] = MappingProxyType(
    {
        "h1": "heading",
        "h2": "heading",
        "h3": "subheading",
        "h4": "subheading",
        "li": "item",
        "dt": "term",
        "blockquote": "quote",
        "figcaption": "note",
    }
)


@dataclass(frozen=True)
class PageTexts:
    content: MonographContent

    def unit(self, ref: str | None, role: Role | None = None) -> ExportText | None:
        unit = self.content.units.get(ref) if ref else None
        if unit is None:
            return None
        runs = _merged(self._runs(unit.nodes, ""))
        if not any(run.text.strip() for run in runs):
            return None
        return ExportText(runs=runs, role=role or TAG_ROLES.get(unit.tag, "body"), lang=unit.lang)

    def plain(self, ref: str | None) -> str:
        text = self.unit(ref)
        return text.plain.strip() if text is not None else ""

    def units(self, refs: Iterable[str | None], role: Role | None = None) -> list[ExportText]:
        found = (self.unit(ref, role) for ref in dict.fromkeys(refs))
        return [text for text in found if text is not None]

    def marker(self, keys: Iterable[str]) -> str:
        sources = self.content.sources
        return marker(sources[key].number for key in keys if key in sources)

    def _runs(self, nodes: Sequence[Any], style: RunStyle) -> Iterator[Run]:
        for node in nodes:
            if isinstance(node, str):
                yield Run(node, style)
                continue
            if not isinstance(node, Mapping):
                continue
            mark = str(node.get(MARK, ""))
            children = node.get(CHILDREN, [])
            yield from self._runs(
                children if isinstance(children, list) else [], MARK_STYLES.get(mark, style)
            )
            if mark == CITE_MARK:
                shown = self.marker(str(key) for key in node.get(SOURCES, []))
                if shown:
                    yield Run(f" {shown}")


def rich_runs(rich: Sequence[str | Styled] | None) -> tuple[Run, ...]:
    runs = (
        Run(part) if isinstance(part, str) else Run(part.text, MARK_STYLES.get(part.style, ""))
        for part in rich or ()
    )
    return _merged(runs)


def page_references(content: MonographContent) -> tuple[ExportReference, ...]:
    ordered = sorted(content.sources.values(), key=lambda source: source.number)
    return tuple(ExportReference(source.number, _reference_text(source), source.url) for source in ordered)


def _reference_text(source: CitedSource) -> str:
    year = str(source.year) if source.year else None
    parts = (source.full_title or source.title, source.publisher, year)
    return CREDIT_SEPARATOR.join(part for part in parts if part)


def _merged(runs: Iterator[Run]) -> tuple[Run, ...]:
    out: list[Run] = []
    for run in runs:
        if out and out[-1].style == run.style:
            out[-1] = Run(out[-1].text + run.text, run.style)
        elif run.text:
            out.append(run)
    return tuple(out)
