from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.research.crafts import CraftRef
from app.research.explainer import Block
from app.research.knowledge_pieces import placed_block
from app.research.sections import SectionSpec, block_id

from .answer_events import stored_follow_ups
from .answer_sections import SectionOutcome, block_in_language
from .answer_translation import AnswerTranslation
from .explainer_events import ExplainerStream, shown_title
from .knowledge_view import section_heading
from .piece_lookup import PieceLookup, ReusedSection
from .section_enrichment import Enrichment, PictureSearches

__all__ = ["REUSED_SECTION_STATE", "ReusedShowing", "reused_follow_ups", "stream_reused"]

REUSED_SECTION_STATE = "WRITING"


@dataclass(frozen=True)
class ReusedShowing:
    stream: ExplainerStream
    titles: Mapping[str, str]
    translation: AnswerTranslation
    enrichment: Enrichment


async def stream_reused(
    specs: Sequence[SectionSpec], lookup: PieceLookup, showing: ReusedShowing
) -> list[SectionOutcome]:
    chosen = [
        (spec, lookup.reused[spec.discipline])
        for spec in sorted(specs, key=lambda spec: spec.order)
        if spec.discipline in lookup.reused
    ]
    placed = {spec.id: _placed(spec, reused) for spec, reused in chosen}
    async with showing.enrichment.searching() as pictures:
        for spec, _ in chosen:
            pictures.start(spec.id, placed[spec.id])
        return [
            await _reused_section(spec, reused, placed[spec.id], showing, pictures) for spec, reused in chosen
        ]


def reused_follow_ups(craft: CraftRef | None, lookup: PieceLookup) -> list[str]:
    if craft is None:
        return []
    views = [
        reused.cited.views[claim_id]
        for reused in lookup.reused.values()
        for piece in reused.pieces
        for claim_id in piece.claim_ids
        if claim_id in reused.cited.views
    ]
    headings = dict.fromkeys(section_heading(view.concept_type) for view in views)
    return stored_follow_ups(craft.name, list(headings))


def _placed(spec: SectionSpec, reused: ReusedSection) -> tuple[Block, ...]:
    return tuple(
        placed_block(piece, block_id(spec.id, ordinal))
        for ordinal, piece in enumerate(reused.pieces, start=1)
    )


async def _reused_section(
    spec: SectionSpec,
    reused: ReusedSection,
    placed: Sequence[Block],
    showing: ReusedShowing,
    pictures: PictureSearches,
) -> SectionOutcome:
    stream = showing.stream
    title = shown_title(spec, showing.titles)["title"]
    for piece in reused.pieces:
        await stream.trail.found_piece(piece.id, title=title, stored_at=piece.created_at)
    await stream.section_started(spec, titles=showing.titles, state=REUSED_SECTION_STATE)
    texts = {claim_id: view.text for claim_id, view in reused.cited.views.items()}
    shown: list[Block] = []
    for block in placed:
        translated = await block_in_language(
            block, stream=stream, translation=showing.translation, claim_texts=texts
        )
        await stream.blocks(spec.id, [translated], reused.cited.sources)
        shown.append(translated)
    images = await pictures.sent(spec.id, stream)
    if images is not None:
        shown.append(images)
    await stream.section_done(spec.id, searched=None)
    return SectionOutcome(
        spec,
        blocks=tuple(shown),
        claim_ids=tuple(dict.fromkeys(claim for piece in reused.pieces for claim in piece.claim_ids)),
        sources=reused.cited.sources,
    )
