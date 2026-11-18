from __future__ import annotations

from collections.abc import Sequence

from app.research.citations import Citation
from app.research.craft_page import OverviewSection
from app.research.craft_parts import (
    RESEARCH_QUESTIONS,
    KeyFactsPart,
    LabelledFact,
    PlatePart,
    RegisterFact,
    RegisterFactsPart,
    StartResearchPart,
)

from .chapter_context import ChapterContext
from .chapter_draft import ChapterDraft, Drafted
from .chapter_plates import PicturePlan
from .chapter_prose import prose_blocks

__all__ = ["GI_WORDS", "glance_chapter"]

KEY = "glance"
GI_WORDS = {"GI": "Registered geographical indication", "NON_GI": "Not a registered geographical indication"}


def glance_chapter(
    ctx: ChapterContext, sections: Sequence[OverviewSection], plan: PicturePlan, questions: Sequence[str]
) -> ChapterDraft:
    items: list[Drafted] = [Drafted.of_block(block) for block in prose_blocks(ctx, KEY, sections)]
    facts = _key_facts(ctx)
    if facts is not None:
        items.append(Drafted.of_part(facts, figure={"kind": "key_facts"}))
    else:
        items += [Drafted.of_part(part) for part in _register_facts(ctx)]
    items += [Drafted.of_part(PlatePart(kind="plate", plate=placed.plate)) for placed in plan.plates(KEY)]
    if not ctx.own and len(questions) == RESEARCH_QUESTIONS:
        items.append(Drafted.of_part(StartResearchPart(kind="start_research", questions=list(questions))))
    return ChapterDraft(KEY, plan.opener(KEY), items)


def _key_facts(ctx: ChapterContext) -> KeyFactsPart | None:
    curated = ctx.records.curated
    if curated is None:
        return None
    facts = []
    for fact in curated.overview.key_facts:
        if not ctx.visible.all_shown(fact.claim_ids):
            continue
        citations: dict[str, Citation] = {}
        for claim_id in fact.claim_ids:
            citations.update((c.id, c) for c in ctx.claims[claim_id].citations)
        facts.append(LabelledFact(label=fact.label, value=fact.value, citations=list(citations.values())))
    return KeyFactsPart(kind="key_facts", facts=facts) if facts else None


def _register_facts(ctx: ChapterContext) -> list[RegisterFactsPart]:
    craft = ctx.records.craft
    rows = [
        ("Family", craft.family_label or craft.category_name),
        ("Kind", craft.kind_label or craft.sub_category_name),
        ("Home state", ", ".join(craft.state_of_origin) or None),
        ("Practised in", ", ".join(craft.state_of_practice) or None),
        ("GI status", GI_WORDS.get(craft.gi_status or "")),
    ]
    facts = [RegisterFact(label=label, value=value) for label, value in rows if value]
    return [RegisterFactsPart(kind="register_facts", facts=facts)] if facts else []
