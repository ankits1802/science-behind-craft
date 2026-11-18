from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence

from app.research.blocks import (
    DifferRead,
    DifferReading,
    ExplainerSentence,
    LadderCondition,
    LadderMaterial,
    LadderStage,
    LadderTool,
    ProcessLadderBlock,
    StageAfter,
)
from app.research.chapter_keys import DISCIPLINE_CHAPTERS
from app.research.citations import Citation
from app.research.craft_page import DifferRow, OverviewSection
from app.research.craft_page_process import PageProcess, PageStage, StageItem
from app.research.craft_parts import PlatePart, SourcesDifferPart
from app.research.quotes import quote_occurs
from app.science.ladder import process_ladder
from app.science.reaction_colours import after_phrase, step_colours

from .chapter_context import ChapterContext
from .chapter_draft import ChapterDraft, Drafted
from .chapter_figures import MAKING_FIGURES, signature_figures
from .chapter_plates import PicturePlan, loose_stage_plates
from .chapter_prose import prose_blocks
from .curated_index import IndexStage
from .curation_keys import TOOL_ROLE

__all__ = ["WHY_DISCIPLINES", "differ_reading", "made_chapter", "with_loose_differ"]

KEY = "made"
LADDER_ID = "made.ladder"
WHY_DISCIPLINES = frozenset({"CHEMISTRY", "MATERIALS", "PHYSICS", "BOTANY"})
TIMING_LABELS = {"DURATION": "Duration", "SEASON": "Season"}
AFTER = "AFTER"
AFTER_TEXT_MAX = 120


def made_chapter(
    ctx: ChapterContext,
    sections: Sequence[OverviewSection],
    plan: PicturePlan,
    v2: tuple[PageProcess, Sequence[DifferRow]],
) -> ChapterDraft:
    process, differ = v2
    items = [Drafted.of_block(block) for block in prose_blocks(ctx, KEY, sections)]
    ladder = process_ladder_block(ctx, process, differ, plan)
    if ladder is not None:
        values = {"craft": ctx.craft_name, "stages": len(ladder.stages)}
        items.append(Drafted.of_block(ladder, figure=values))
    items += [
        Drafted.of_block(figure, figure={"kind": figure.kind})
        for figure in signature_figures(ctx, MAKING_FIGURES, KEY)
    ]
    laddered = {stage.stage_id for stage in ladder.stages} if ladder is not None else set()
    items += [Drafted.of_part(plate) for plate in loose_stage_plates(plan, laddered)]
    items += [Drafted.of_part(PlatePart(kind="plate", plate=p.plate)) for p in plan.plates(KEY)]
    return ChapterDraft(KEY, plan.opener(KEY), items)


def process_ladder_block(
    ctx: ChapterContext, process: PageProcess, differ: Sequence[DifferRow], plan: PicturePlan
) -> ProcessLadderBlock | None:
    if process.process_id is None or not process.stages:
        return None
    built = process_ladder(
        ctx.process(), block_id=LADDER_ID, stage_ids=[stage.id for stage in process.stages]
    )
    if built is None or built.process_id != process.process_id:
        return None
    shown = {stage.id: stage for stage in process.stages}
    rows = {row.key: row for row in differ}
    stages = [
        _enriched(ctx, stage, shown[stage.stage_id], (rows, plan), position)
        for position, stage in enumerate(built.stages, start=1)
        if stage.stage_id in shown
    ]
    return built.model_copy(update={"stages": stages}) if stages else None


def _enriched(
    ctx: ChapterContext,
    stage: LadderStage,
    page: PageStage,
    found: tuple[Mapping[str, DifferRow], PicturePlan],
    position: int,
) -> LadderStage:
    rows, plan = found
    entry = _index_stage(ctx, stage.stage_id)
    materials, tools = _items(ctx, stage, page)
    update = {
        "local_name": page.local_name,
        "unnumbered": True if page.order is None else None,
        "materials": materials,
        "tools": tools,
        "conditions": [*stage.conditions, *_timing(ctx, page, stage.conditions)],
        "after": _after(ctx, entry, stage),
        "why": _why(ctx, entry, page, stage),
        "differs": [differ_reading(ctx, rows[key], stage.sentences) for key in page.differ if key in rows],
        "pictures": plan.stage_pictures(stage.stage_id),
    }
    return LadderStage.model_validate({**stage.model_dump(by_alias=True), **_present(update)})


def differ_reading(
    ctx: ChapterContext, row: DifferRow, shown: Sequence[ExplainerSentence] = ()
) -> DifferReading:
    by_claim = {citation.claim_id: sentence.id for sentence in shown for citation in sentence.citations}
    reads = []
    for n, claim_id in enumerate(row.claim_ids, start=1):
        sentence_id = by_claim.get(str(claim_id))
        sentence = None if sentence_id else ctx.sentence(claim_id, f"{row.key}.{n}")
        reads.append(DifferRead(sentence=sentence, shown_in=sentence_id))
    return DifferReading(key=row.key, about=row.about, weight=row.weight, readings=reads)


def _present(update: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in update.items() if value not in (None, [], ())}


def _index_stage(ctx: ChapterContext, stage_id: uuid.UUID) -> IndexStage | None:
    curated = ctx.records.curated
    return next((entry for entry in curated.stages if entry.stage_id == stage_id), None) if curated else None


def _items(
    ctx: ChapterContext, stage: LadderStage, page: PageStage
) -> tuple[list[LadderMaterial], list[LadderTool]]:
    uses = {material.id: material.material_id for material in ctx.records.process.materials}
    named: dict[uuid.UUID, StageItem] = {item.id: item for item in [*page.materials, *page.tools]}
    materials, tools = [], []
    for material in stage.materials:
        item = named.get(uses.get(material.material_id) or material.material_id)
        if material.role == TOOL_ROLE:
            if item is not None:
                tools.append(_tool(ctx, item, material.citations))
            continue
        materials.append(_named(material, item))
    return materials, tools


def _named(material: LadderMaterial, item: StageItem | None) -> LadderMaterial:
    if item is None:
        return material
    update = {
        "botanical_name": item.botanical_name,
        "pubchem_cid": item.pubchem_cid,
        "local_names": item.local_names,
    }
    return material.model_copy(update=_present(update))


def _tool(ctx: ChapterContext, item: StageItem, cited: Sequence[Citation]) -> LadderTool:
    citations = {c.id: c for c in cited}
    for claim_id in item.claim_ids:
        citations.update((c.id, c) for c in ctx.claims[claim_id].citations)
    return LadderTool(
        tool_id=item.id, name=item.name, local_names=item.local_names, citations=list(citations.values())
    )


def _timing(ctx: ChapterContext, page: PageStage, have: Sequence[LadderCondition]) -> list[LadderCondition]:
    stated = {condition.stated for condition in have}
    found = []
    for timing in page.timing:
        claim = ctx.claims.get(timing.claim_id)
        quoted = (
            [c for c in claim.citations if c.quote and quote_occurs(timing.text, c.quote)] if claim else []
        )
        if quoted and timing.text not in stated:
            found.append(
                LadderCondition(label=TIMING_LABELS[timing.kind], stated=timing.text, citations=quoted)
            )
    return found


def _after(ctx: ChapterContext, entry: IndexStage | None, stage: LadderStage) -> StageAfter | None:
    if entry is not None and entry.after is not None and entry.after.claim_id in ctx.claims:
        claim = ctx.claims[entry.after.claim_id]
        return StageAfter(text=entry.after.text, colours=entry.after.colours, citations=list(claim.citations))
    cited = [citation for sentence in stage.sentences for citation in sentence.citations]
    after = next((colour for colour in step_colours(cited) if colour.side == AFTER), None)
    text = after_phrase(after.stated, AFTER_TEXT_MAX) if after is not None else None
    if after is None or text is None:
        return None
    return StageAfter(text=text, colours=[after.colour], citations=after.citations)


def _why(
    ctx: ChapterContext, entry: IndexStage | None, page: PageStage, stage: LadderStage
) -> ExplainerSentence | None:
    shown = {citation.claim_id for sentence in stage.sentences for citation in sentence.citations}
    sentence_id = f"{LADDER_ID}.why{stage.ordinal}"
    if entry is not None and entry.why_claim_id is not None:
        return None if str(entry.why_claim_id) in shown else ctx.sentence(entry.why_claim_id, sentence_id)
    candidates = [*page.claim_ids, *(c for item in page.materials for c in item.claim_ids)]
    for claim_id in ctx.ordered(candidates):
        claim = ctx.claims[claim_id]
        if str(claim_id) not in shown and claim.discipline in WHY_DISCIPLINES and claim.level != "HYPOTHESIS":
            return ctx.sentence(claim_id, sentence_id)
    return None


def with_loose_differ(
    ctx: ChapterContext, drafts: Sequence[ChapterDraft], v2: tuple[PageProcess, Sequence[DifferRow]]
) -> list[ChapterDraft]:
    process, differ = v2
    held = {key for stage in process.stages for key in stage.differ}
    placed: dict[str, list[Drafted]] = {}
    for row in differ:
        if row.key in held:
            continue
        claim = ctx.claims.get(row.claim_ids[0])
        chapter = DISCIPLINE_CHAPTERS.get(claim.discipline) if claim is not None else None
        if chapter is not None:
            part = SourcesDifferPart(kind="sources_differ", reading=differ_reading(ctx, row))
            placed.setdefault(chapter, []).append(Drafted.of_part(part))
    return [
        ChapterDraft(draft.key, draft.opener, [*draft.items, *placed.get(draft.key, [])]) for draft in drafts
    ]
