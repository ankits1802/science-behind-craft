from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from pydantic import Field

from .base import ContractModel
from .monograph_page import MonographContent
from .page_render import INTERACTIVE_KINDS, MAP_KINDS
from .page_report_rules import OPENING, PICTURE_KIND

__all__ = [
    "AUTHORED_CHAPTERS",
    "BAR_NOTE",
    "BAR_SLUG",
    "BarCounts",
    "ChapterCounts",
    "Counts",
    "bar_counts",
    "chapter_key",
    "chapter_order",
    "content_counts",
    "total_counts",
]

BAR_SLUG = "Kutch-Ajrakh"
BAR_NOTE = (
    "Guidance only: the counts of this page beside Kutch Ajrakh's, the approved bar, chapter by chapter. "
    "A count never passes or fails a page; the rules do."
)
AUTHORED_CHAPTERS: Mapping[str, str] = MappingProxyType(
    {
        "answer": OPENING,
        "cloth": "glance",
        "chemistry": "chem",
        "why-kachchh": "why",
        "what-if": "whatif",
    }
)


class Counts(ContractModel):
    pictures: int = Field(default=0, ge=0)
    figures: int = Field(default=0, ge=0)
    interactives: int = Field(default=0, ge=0)
    maps: int = Field(default=0, ge=0)


class ChapterCounts(ContractModel):
    chapter: str
    page: Counts
    bar: Counts


class BarCounts(ContractModel):
    bar_slug: str = BAR_SLUG
    page: Counts
    bar: Counts
    chapters: list[ChapterCounts]
    note: str = BAR_NOTE


def chapter_key(chapter: str) -> str:
    return AUTHORED_CHAPTERS.get(chapter, chapter)


def content_counts(content: MonographContent) -> dict[str, Counts]:
    found: dict[str, Counts] = {}
    for component in content.components:
        key = chapter_key(component.chapter)
        found[key] = _added(found.get(key, Counts()), component.kind)
    return found


def bar_counts(page: MonographContent, bar: MonographContent) -> BarCounts:
    mine, theirs = content_counts(page), content_counts(bar)
    order = dict.fromkeys([*chapter_order(page), *mine, *chapter_order(bar), *theirs])
    chapters = [
        ChapterCounts(chapter=key, page=mine.get(key, Counts()), bar=theirs.get(key, Counts()))
        for key in order
    ]
    return BarCounts(page=total_counts(mine.values()), bar=total_counts(theirs.values()), chapters=chapters)


def total_counts(rows: Iterable[Counts]) -> Counts:
    listed = list(rows)
    return Counts(
        pictures=sum(row.pictures for row in listed),
        figures=sum(row.figures for row in listed),
        interactives=sum(row.interactives for row in listed),
        maps=sum(row.maps for row in listed),
    )


def chapter_order(content: MonographContent) -> list[str]:
    return list(dict.fromkeys(chapter_key(entry.chapter) for entry in content.layout))


def _added(counts: Counts, kind: str) -> Counts:
    if kind == PICTURE_KIND:
        return counts.model_copy(update={"pictures": counts.pictures + 1})
    return counts.model_copy(
        update={
            "figures": counts.figures + 1,
            "interactives": counts.interactives + (kind in INTERACTIVE_KINDS),
            "maps": counts.maps + (kind in MAP_KINDS),
        }
    )
