from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .coverage_chapters import field_chapter
from .monograph_document import MonographDocument
from .page_proposal_review import PART_QUEUES, TITLE_MAX_CHARS, ProposalPart
from .page_proposals import ACCEPTED, COMPONENT, FACT, LAYOUT, STRUCTURE, PageBundle, PartReport
from .page_report_rules import PICTURE_KIND

__all__ = ["LAYOUT_TITLE", "PICTURE_TITLE", "proposal_parts"]

LAYOUT_TITLE = "The page's layout: where each chapter's parts are placed"
PICTURE_TITLE = "A picture given to the page"
ELLIPSIS = "…"
UUID_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@dataclass(frozen=True)
class _Plate:
    label: str
    chapter: str
    title: str


def proposal_parts(
    bundle: PageBundle, reports: Sequence[PartReport], after: MonographDocument | None
) -> list[ProposalPart]:
    chapters = _component_chapters(after)
    plates = _plates(after)
    found: list[ProposalPart] = []
    for report in reports:
        ident = _ident(report)
        if ident is None or report.outcome != ACCEPTED or report.part not in PART_QUEUES:
            continue
        found.append(_part(bundle, report, ident, (chapters, plates)))
    return found


def _part(
    bundle: PageBundle,
    report: PartReport,
    ident: uuid.UUID,
    placed: tuple[Mapping[str, str], Mapping[str, _Plate]],
) -> ProposalPart:
    chapters, plates = placed
    if report.part == FACT:
        fact = bundle.facts[report.index]
        return _made(FACT, ident, (field_chapter(fact.field), None), fact.statement)
    if report.part == STRUCTURE:
        item = bundle.structure[report.index]
        chapter = field_chapter(item.field) if item.field is not None else None
        return _made(STRUCTURE, ident, (chapter, None), item.statement or _words(item.item.kind))
    if report.part == COMPONENT:
        body = bundle.components[report.index].proposal
        chapter = chapters.get(body.label) or field_chapter(body.field)
        return _made(COMPONENT, ident, (chapter, body.label), body.title)
    if report.part == LAYOUT:
        return _made(LAYOUT, ident, (None, None), LAYOUT_TITLE)
    plate = plates.get(str(ident))
    if plate is None:
        return _made(report.part, ident, (None, None), PICTURE_TITLE)
    return _made(report.part, ident, (plate.chapter, plate.label), plate.title)


def _made(part: str, ident: uuid.UUID, place: tuple[str | None, str | None], title: str) -> ProposalPart:
    chapter, label = place
    shown = title if len(title) <= TITLE_MAX_CHARS else title[: TITLE_MAX_CHARS - 1].rstrip() + ELLIPSIS
    return ProposalPart.model_validate(
        {
            "part": part,
            "kind": PART_QUEUES[part],
            "id": ident,
            "chapter": chapter,
            "label": label,
            "title": shown,
        }
    )


def _ident(report: PartReport) -> uuid.UUID | None:
    if report.id is None:
        return None
    try:
        return uuid.UUID(report.id)
    except ValueError:
        return None


def _component_chapters(after: MonographDocument | None) -> dict[str, str]:
    if after is None:
        return {}
    return {entry.label: entry.chapter for entry in after.content.components}


def _plates(after: MonographDocument | None) -> dict[str, _Plate]:
    if after is None:
        return {}
    found: dict[str, _Plate] = {}
    for entry in after.content.components:
        if entry.kind != PICTURE_KIND:
            continue
        spec = json.dumps(after.specs.get(entry.label, {}))
        for ident in _named_ids(spec):
            found.setdefault(ident, _Plate(entry.label, entry.chapter, entry.title))
    return found


def _named_ids(spec: str) -> list[str]:
    return list(dict.fromkeys(UUID_TEXT.findall(spec)))


def _words(code: str) -> str:
    text = code.replace("_", " ").lower()
    return text[:1].upper() + text[1:]
