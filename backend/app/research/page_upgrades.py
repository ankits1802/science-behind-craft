from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from app.core.clock import INDIA_TZ

from .component_specs_general import GENERAL_MAP_LAYER
from .component_specs_map_parts import MapParts
from .coverage_chapters import field_chapter
from .monograph_document import MonographDocument
from .open_work_texts import counted
from .page_report_drawable import PLACE_FIELD, HeldShapes, opportunities
from .page_report_rules import ReadPage, Sentence

__all__ = [
    "MAP_PARTS",
    "PROSE_RUN_MIN",
    "UPGRADE_CUTOFF",
    "UPGRADE_FACTS_MAX",
    "upgrade_lines",
]

UPGRADE_CUTOFF = datetime(2026, 11, 26, 11, 21, tzinfo=INDIA_TZ)
MAP_PARTS = tuple(MapParts.model_fields)
PROSE_RUN_MIN = 3
UPGRADE_FACTS_MAX = 6
NO_MAP = (
    "{chapter}: {count} of places, stated by {facts}, and no places map; a map_layer declared from them is "
    "drawn on the site's own base, framed to its places with relief, rivers, district lines and the India "
    "locator, and may name a frame, layers to emphasise, routes, rings, district values or a sequence, "
    "each cited (decision 0232)"
)
BARE_MAP = (
    "{chapter}: the places map {label} is drawn on the site's own base now but says only where its places "
    "are; it could say what it is about with a frame, layers to emphasise, routes, rings, district values "
    "or a sequence the facts state, each cited (decision 0232)"
)
PROSE_RUN = (
    "{chapter}: {count} run on with no figure, stated by {facts}; Kutch Ajrakh draws a figure in every "
    "chapter of cited prose, so a figure could carry what they state, among them a coded_figure written "
    "over the chapter's cited data (decision 0231)"
)


def upgrade_lines(document: MonographDocument, held: HeldShapes | None) -> list[str]:
    page = ReadPage.of(document)
    found = opportunities(document.content, page.sentences, held)
    named = {opportunity.chapter for opportunity in found}
    maps = _map_lines(page, document.specs)
    if maps:
        named.add(field_chapter(PLACE_FIELD))
    return [
        *(opportunity.line() for opportunity in found),
        *maps,
        *_prose_lines(page, named),
    ]


def _map_lines(page: ReadPage, specs: Mapping[str, Mapping[str, Any]]) -> list[str]:
    placed = [sentence for sentence in page.sentences if sentence.field == PLACE_FIELD]
    maps = [entry for entry in page.figures if entry.kind == GENERAL_MAP_LAYER]
    chapter = field_chapter(PLACE_FIELD)
    if not maps:
        if not placed:
            return []
        return [NO_MAP.format(chapter=chapter, count=counted(len(placed), "sentence"), facts=_facts(placed))]
    return [
        BARE_MAP.format(chapter=entry.chapter, label=entry.label)
        for entry in maps
        if not any(specs.get(entry.label, {}).get(part) for part in MAP_PARTS)
    ]


def _prose_lines(page: ReadPage, named: set[str]) -> list[str]:
    prose: dict[str, list[Sentence]] = defaultdict(list)
    for sentence in page.sentences:
        prose[sentence.chapter].append(sentence)
    drawn = {entry.chapter for entry in page.figures}
    return [
        PROSE_RUN.format(chapter=chapter, count=counted(len(run), "cited paragraph"), facts=_facts(run))
        for chapter, run in prose.items()
        if len(run) >= PROSE_RUN_MIN and chapter not in drawn and chapter not in named
    ]


def _facts(sentences: Sequence[Sentence]) -> str:
    claims = list(dict.fromkeys(_claims(sentences)))
    shown = ", ".join(claims[:UPGRADE_FACTS_MAX])
    more = len(claims) - UPGRADE_FACTS_MAX
    return f"{shown} and {more} more" if more > 0 else shown


def _claims(sentences: Iterable[Sentence]) -> Iterable[str]:
    return (claim for sentence in sentences for claim in sentence.claim_ids)
