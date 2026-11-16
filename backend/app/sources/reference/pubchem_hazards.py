from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ..records import clean_text, https_or_none

__all__ = ["GHS_MAX_SOURCES", "HazardReport", "HazardSource", "hazard_report"]

GHS_MAX_SOURCES = 3
LEFT_OUT = frozenset({"Precautionary Statement Codes"})
PICTOGRAMS = "Pictogram(s)"


@dataclass(frozen=True)
class HazardSource:
    name: str
    url: str | None
    licence_url: str | None
    lines: tuple[str, ...]


@dataclass(frozen=True)
class HazardReport:
    title: str
    sources: tuple[HazardSource, ...] = field(default_factory=tuple)

    @property
    def licence(self) -> str | None:
        urls = list(dict.fromkeys(s.licence_url for s in self.sources if s.licence_url))
        return "; ".join(urls) or None

    @property
    def attribution(self) -> str:
        return "; ".join(f"Source: {s.name}" + (f", {s.url}" if s.url else "") for s in self.sources)

    def text(self, cid: str) -> str:
        lines = [f"{self.title} (PubChem CID {cid}): GHS classification"]
        for source in self.sources:
            lines.append(f"Reported by {source.name}:")
            lines.extend(source.lines)
        return "\n".join(lines)


def hazard_report(record: Mapping[str, Any]) -> HazardReport | None:
    title = clean_text(record.get("RecordTitle"))
    if title is None:
        return None
    lines_by_reference: dict[int, list[str]] = {}
    for info in _information(record.get("Section") or []):
        if info.get("Name") in LEFT_OUT or not isinstance(info.get("ReferenceNumber"), int):
            continue
        lines_by_reference.setdefault(info["ReferenceNumber"], []).extend(_lines(info))
    references = {ref.get("ReferenceNumber"): ref for ref in record.get("Reference") or []}
    sources = [
        _source(references.get(number) or {}, lines) for number, lines in lines_by_reference.items() if lines
    ]
    named = tuple(source for source in sources if source is not None)[:GHS_MAX_SOURCES]
    return HazardReport(title, named) if named else None


def _information(sections: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = []
    for section in sections:
        found.extend(section.get("Information") or [])
        found.extend(_information(section.get("Section") or []))
    return found


def _lines(info: Mapping[str, Any]) -> list[str]:
    name = clean_text(info.get("Name"))
    strings = (info.get("Value") or {}).get("StringWithMarkup") or []
    if name == PICTOGRAMS:
        icons = [
            clean_text(m.get("Extra"))
            for s in strings
            for m in s.get("Markup") or []
            if m.get("Type") == "Icon"
        ]
        values = [icon for icon in icons if icon]
        return [f"{name}: {', '.join(values)}"] if values else []
    values = [text for text in (clean_text(s.get("String")) for s in strings) if text]
    if not name or not values:
        return []
    if len(values) == 1:
        return [f"{name}: {values[0]}"]
    return [f"{name}:", *values]


def _source(reference: Mapping[str, Any], lines: list[str]) -> HazardSource | None:
    name = clean_text(reference.get("SourceName"))
    if name is None:
        return None
    return HazardSource(
        name=name,
        url=https_or_none(reference.get("URL")),
        licence_url=https_or_none(reference.get("LicenseURL")),
        lines=tuple(lines),
    )
