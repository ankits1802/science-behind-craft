from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from app.core.errors import InvalidInput

from .base import ContractModel, absent, empty
from .chapter_keys import CHAPTER_KEYS
from .coverage import FieldCoverage
from .coverage_chapters import field_chapter
from .knowledge_api import Fact
from .monograph_document import MonographDocument
from .monograph_page import MonographContent
from .page_layout import PageLayout
from .page_report_drawable import HeldShapes, opportunities
from .page_report_rules import HEADING_TAG, PICTURE_KIND, ReadPage, node_text
from .vocabulary import Discipline

__all__ = [
    "BRIEF_BYTES_MAX",
    "CURSOR_PATTERN",
    "LINE_CHARS",
    "PAGE_BRIEF_SCHEMA_VERSION",
    "BriefChapter",
    "BriefField",
    "BriefFigure",
    "BriefInput",
    "ChapterFacts",
    "FactLine",
    "PageBrief",
    "brief_bytes",
    "fact_line",
    "page_brief",
]

PAGE_BRIEF_SCHEMA_VERSION = 1
BRIEF_BYTES_MAX = 40_000
LINE_CHARS = 120
DIGEST_CHARS = 12
CURSOR_PATTERN = rf"^[0-9]{{1,6}}:[0-9a-f]{{{DIGEST_CHARS}}}$"
CURSOR_ROOM = 48
GROUP_BYTES = len('{"chapter":"","facts":[]},')
ELLIPSIS = "…"
CHAPTER_HEAD = "h2"
UNFILED_CHAPTER = CHAPTER_KEYS[0]
SPACES = re.compile(r"\s+")
STALE_CURSOR = "The page's facts changed since this cursor was given; read the brief again from its start, without a cursor."
PAST_THE_END = "This cursor names no fact left to send; the brief has sent all {total}."


class BriefField(ContractModel):
    field: Discipline
    claims: int = Field(ge=0)
    standing: str


class BriefFigure(ContractModel):
    label: str
    kind: str
    title: str
    role: str | None = Field(default=None, exclude_if=absent)
    size: str | None = Field(default=None, exclude_if=absent)


class BriefChapter(ContractModel):
    chapter: str
    title: str | None = Field(default=None, exclude_if=absent)
    headings: list[str] = Field(default_factory=list, exclude_if=empty)
    fields: list[BriefField] = Field(default_factory=list, exclude_if=empty)
    sentences: int = Field(ge=0)
    figures: list[BriefFigure] = Field(default_factory=list, exclude_if=empty)
    pictures: int = Field(ge=0)
    facts: int = Field(ge=0)


class FactLine(ContractModel):
    id: uuid.UUID
    line: str


class ChapterFacts(ContractModel):
    chapter: str
    facts: list[FactLine]


class PageBrief(ContractModel):
    schema_version: Literal[1] = PAGE_BRIEF_SCHEMA_VERSION
    name: str
    lede: list[str] = Field(default_factory=list, exclude_if=empty)
    chapters: list[BriefChapter] = Field(default_factory=list, exclude_if=empty)
    opportunities: list[str] = Field(default_factory=list, exclude_if=empty)
    layout_version: int | None = Field(default=None, exclude_if=absent)
    facts_total: int = Field(ge=0)
    facts_before: int = Field(ge=0)
    facts: list[ChapterFacts]
    cursor: str | None = None


@dataclass(frozen=True)
class BriefInput:
    name: str
    slug: str
    facts: Sequence[Fact]
    coverage: FieldCoverage | None = None
    document: MonographDocument | None = None
    layout: PageLayout | None = None
    held: HeldShapes | None = None


Placed = tuple[str, FactLine]
Drawn = tuple[MonographContent, Mapping[str, int]]


def fact_line(text: str, limit: int = LINE_CHARS) -> str:
    said = SPACES.sub(" ", text).strip()
    if len(said) <= limit:
        return said
    cut = said[: limit - len(ELLIPSIS)]
    word = cut.rsplit(" ", 1)[0] if " " in cut else cut
    return word.rstrip(" ,;:") + ELLIPSIS


def brief_bytes(model: BaseModel) -> int:
    dumped = model.model_dump(mode="json", by_alias=True)
    return len(json.dumps(dumped, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def page_brief(given: BriefInput, cursor: str | None = None) -> PageBrief:
    placed = _placed(given.facts)
    start = _start(cursor, placed)
    head = _outline(given, placed) if start == 0 else {}
    empty_page = PageBrief(name=given.name, facts_total=len(placed), facts_before=start, facts=[], **head)
    end = _end(brief_bytes(empty_page), placed, start)
    following = f"{end}:{_digest(placed)}" if end < len(placed) else None
    return empty_page.model_copy(update={"facts": _grouped(placed[start:end]), "cursor": following})


def _placed(facts: Sequence[Fact]) -> list[Placed]:
    order = {chapter: rank for rank, chapter in enumerate(CHAPTER_KEYS)}
    lines = [(_chapter_of(fact), FactLine(id=fact.id, line=fact_line(fact.text))) for fact in facts]
    return sorted(lines, key=lambda placed: order.get(placed[0], len(order)))


def _chapter_of(fact: Fact) -> str:
    return field_chapter(fact.field) if fact.field else UNFILED_CHAPTER


def _digest(placed: Sequence[Placed]) -> str:
    joined = "\n".join(str(line.id) for _, line in placed)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:DIGEST_CHARS]


def _start(cursor: str | None, placed: Sequence[Placed]) -> int:
    if cursor is None:
        return 0
    offset, _, digest = cursor.partition(":")
    if digest != _digest(placed):
        raise InvalidInput(STALE_CURSOR)
    if int(offset) >= len(placed):
        raise InvalidInput(PAST_THE_END.format(total=len(placed)))
    return int(offset)


def _end(used: int, placed: Sequence[Placed], start: int) -> int:
    total, chapter, end = used + CURSOR_ROOM, None, start
    for key, line in placed[start:]:
        cost = brief_bytes(line) + 1 + (GROUP_BYTES + len(key) if key != chapter else 0)
        if end > start and total + cost > BRIEF_BYTES_MAX:
            break
        total, chapter, end = total + cost, key, end + 1
    return end


def _grouped(placed: Sequence[Placed]) -> list[ChapterFacts]:
    groups: list[tuple[str, list[FactLine]]] = []
    for key, line in placed:
        if not groups or groups[-1][0] != key:
            groups.append((key, []))
        groups[-1][1].append(line)
    return [ChapterFacts(chapter=key, facts=lines) for key, lines in groups]


def _outline(given: BriefInput, placed: Sequence[Placed]) -> dict[str, object]:
    content = given.document.content if given.document is not None else _no_content(given.slug)
    page = ReadPage.of(given.document) if given.document is not None else None
    sentences = page.sentences if page is not None else ()
    found = opportunities(content, sentences, given.held)
    said = Counter(sentence.chapter for sentence in sentences)
    return {
        "lede": [sentence.text for sentence in page.lede()] if page is not None else [],
        "chapters": _chapters(given, (content, said), placed),
        "opportunities": [opportunity.line() for opportunity in found],
        "layout_version": given.layout.version if given.layout is not None else None,
    }


def _no_content(slug: str) -> MonographContent:
    return MonographContent(
        craft_slug=slug,
        sources={},
        citations={},
        citation_claims={},
        data={},
        units={},
        components=[],
        layout=[],
    )


def _chapters(given: BriefInput, page: Drawn, placed: Sequence[Placed]) -> list[BriefChapter]:
    fields = given.coverage.fields if given.coverage is not None else []
    named = {field_chapter(count.field) for count in fields} | {key for key, _ in placed}
    named |= {entry.chapter for entry in page[0].layout}
    return [_chapter(key, given, page, placed) for key in CHAPTER_KEYS if key in named]


def _chapter(key: str, given: BriefInput, page: Drawn, placed: Sequence[Placed]) -> BriefChapter:
    content, said = page
    units = [
        content.units[entry.ref]
        for entry in content.layout
        if entry.chapter == key
        and entry.kind == "unit"
        and entry.within is None
        and entry.ref in content.units
    ]
    heads = [node_text(unit.nodes).strip() for unit in units if unit.tag == CHAPTER_HEAD]
    counts = given.coverage.fields if given.coverage is not None else []
    return BriefChapter(
        chapter=key,
        title=heads[0] if heads else None,
        headings=[node_text(unit.nodes).strip() for unit in units if unit.tag == HEADING_TAG],
        fields=[
            BriefField(field=count.field, claims=count.claims, standing=count.standing)
            for count in counts
            if field_chapter(count.field) == key
        ],
        sentences=said.get(key, 0),
        figures=_figures(key, content, given.layout),
        pictures=sum(1 for c in content.components if c.chapter == key and c.kind == PICTURE_KIND),
        facts=sum(1 for chapter, _ in placed if chapter == key),
    )


def _figures(key: str, content: MonographContent, layout: PageLayout | None) -> list[BriefFigure]:
    shown = [c for c in content.components if c.chapter == key and c.kind != PICTURE_KIND]
    entries = {entry.ref: entry for entry in layout.entries} if layout is not None else {}
    return [
        BriefFigure(
            label=c.label,
            kind=c.kind,
            title=fact_line(c.title),
            role=entries[c.label].role if c.label in entries else None,
            size=entries[c.label].size if c.label in entries else None,
        )
        for c in shown
    ]
