from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from app.research.blocks import ProcessLadderBlock
from app.research.chapter_keys import CHAPTER_TITLES
from app.research.craft_chapters import Chapter, ChapterItem, FigureHead, figure_title
from app.research.craft_parts import (
    CommunitiesPart,
    ContributedPart,
    OpenQuestionsPart,
    PagePart,
    PagePlate,
    PlacesPart,
    PlatePart,
    RecordPart,
    SourcesDifferPart,
)
from app.research.explainer import Block

from .chapter_draft import ChapterDraft, Drafted
from .chapter_ledger import PageLedger

__all__ = ["admitted_chapters", "chapter_title"]

WHERE_IT_IS_MADE = "Where it is made"
HYPOTHESIS = "HYPOTHESIS"
MARKET_ONLY = "Market"

PartFilter = Callable[[PageLedger, Any], PagePart | None]


def chapter_title(key: str, *, place: str | None, gi: bool) -> str:
    if key == "why":
        return CHAPTER_TITLES[key].format(place=place) if place else WHERE_IT_IS_MADE
    if key == "market" and not gi:
        return MARKET_ONLY
    return CHAPTER_TITLES[key]


def admitted_chapters(
    drafts: Sequence[ChapterDraft], ledger: PageLedger, *, place: str | None, gi: bool
) -> list[Chapter]:
    chapters = []
    for draft in drafts:
        opener = _plate(ledger, draft.opener) if draft.opener else None
        items = _admitted_items(draft, ledger)
        if items:
            title = chapter_title(draft.key, place=place, gi=gi)
            chapters.append(Chapter(key=draft.key, title=title, opener=opener, items=items))
    return chapters


def _admitted_items(draft: ChapterDraft, ledger: PageLedger) -> list[ChapterItem]:
    blocks = [drafted.block for drafted in draft.items if drafted.block is not None]
    kept = {block.id: block for block in ledger.blocks(draft.key, blocks)}
    items = []
    for drafted in draft.items:
        if drafted.block is not None:
            block = kept.get(drafted.block.id)
            shown: Block | PagePart | None = _ladder(ledger, block) if block is not None else None
        elif isinstance(drafted.part, RecordPart):
            shown, loose = _record(ledger, drafted.part)
            items += [_item(Drafted.of_part(plate), plate) for plate in loose]
        else:
            shown = _part(ledger, drafted.part)
        if shown is not None:
            items.append(_item(drafted, shown))
    return items


def _item(drafted: Drafted, shown: Any) -> ChapterItem:
    figure: FigureHead | None = None
    if drafted.figure:
        figure = figure_title(drafted.kind, drafted.figure)
        if figure is not None and drafted.borrowed:
            figure = figure.model_copy(update={"borrowed": list(drafted.borrowed)})
    is_block = drafted.block is not None
    return ChapterItem(
        block=shown if is_block else None,
        part=None if is_block else shown,
        figure=figure,
        origin=drafted.origin,
        piece_id=drafted.piece_id,
    )


def _ladder(ledger: PageLedger, block: Block) -> Block:
    if not isinstance(block, ProcessLadderBlock):
        return block
    stages = []
    for stage in block.stages:
        why = stage.why if stage.why is not None and ledger.shown_in(stage.why) is None else None
        if why is not None:
            ledger.note([why])
        differs = [ledger.reading(reading) for reading in stage.differs]
        stages.append(stage.model_copy(update={"why": why, "differs": differs}))
    return block.model_copy(update={"stages": stages})


def _part(ledger: PageLedger, part: PagePart | None) -> PagePart | None:
    if part is None:
        return None
    if isinstance(part, PlatePart):
        return part.model_copy(update={"plate": _plate(ledger, part.plate)})
    if isinstance(part, PlacesPart):
        return _story(ledger, part, "places")
    if isinstance(part, CommunitiesPart):
        return _story(ledger, part, "communities")
    if isinstance(part, SourcesDifferPart):
        return part.model_copy(update={"reading": ledger.reading(part.reading)})
    if isinstance(part, OpenQuestionsPart):
        return _questions(ledger, part)
    if isinstance(part, ContributedPart):
        return _contributed(ledger, part)
    ledger.note(part.cited_sentences())
    return part


def _questions(ledger: PageLedger, part: OpenQuestionsPart) -> OpenQuestionsPart | None:
    kept = []
    for question in part.questions:
        sentences = [s for s in question.sentences if s.level == HYPOTHESIS or ledger.shown_in(s) is None]
        ledger.note(sentences)
        if sentences:
            kept.append(question.model_copy(update={"sentences": sentences}))
    return part.model_copy(update={"questions": kept}) if kept else None


def _contributed(ledger: PageLedger, part: ContributedPart) -> ContributedPart:
    shown = [plate.model_copy(update={"sentences": ledger.fresh(plate.sentences)}) for plate in part.pictures]
    return part.model_copy(update={"pictures": shown})


def _plate(ledger: PageLedger, plate: PagePlate) -> PagePlate:
    return plate.model_copy(update={"sentences": ledger.fresh(plate.sentences)})


def _record(ledger: PageLedger, part: RecordPart) -> tuple[RecordPart | None, list[PlatePart]]:
    entries = []
    loose = []
    for entry in part.entries:
        sentences = ledger.fresh(entry.sentences)
        plate = _plate(ledger, entry.plate) if entry.plate else None
        if sentences:
            entries.append(entry.model_copy(update={"sentences": sentences, "plate": plate}))
        elif plate is not None:
            loose.append(PlatePart(kind="plate", plate=plate))
    return (part.model_copy(update={"entries": entries}) if entries else None), loose


def _story(ledger: PageLedger, part: Any, field: str) -> PagePart | None:
    kept = []
    for row in getattr(part, field):
        sentences = ledger.fresh(row.sentences)
        if sentences:
            kept.append(row.model_copy(update={"sentences": sentences}))
    return part.model_copy(update={field: kept}) if kept else None
