from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.research.crafts import CraftRef
from app.research.explainer import Block
from app.research.knowledge_pieces import placed_block
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec, block_id

from .answer_events import stored_follow_ups
from .answer_sections import SectionOutcome
from .answer_translation import AnswerTranslation
from .block_builders import AddedBlocks, BlockBuilders, SectionBuilds
from .builder_interface import BuildAsk
from .explainer_events import ExplainerStream, shown_title
from .knowledge_view import section_heading
from .piece_lookup import PieceLookup, ReusedSection
from .section_enrichment import Enrichment, PictureSearches
from .section_language import block_in_language

__all__ = ["REUSED_SECTION_STATE", "ReuseBuilds", "ReusedShowing", "reused_follow_ups", "stream_reused"]

REUSED_SECTION_STATE = "WRITING"


@dataclass(frozen=True)
class ReuseBuilds:
    builders: BlockBuilders
    answer_id: uuid.UUID
    request: PlanRequest

    def ask(self, spec: SectionSpec, placed: Sequence[Block], reused: ReusedSection) -> BuildAsk:
        return BuildAsk(self.answer_id, spec, self.request, tuple(placed), reused.cited)


@dataclass(frozen=True)
class ReusedShowing:
    stream: ExplainerStream
    titles: Mapping[str, str]
    translation: AnswerTranslation
    enrichment: Enrichment
    builds: ReuseBuilds


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
    async with showing.builds.builders.building() as builds:
        builds.start(showing.builds.ask(spec, placed, reused))
        shown = [await _sent(spec, block, reused, showing, reused.cited.sources) for block in placed]
        rebuilt = await _rebuilt(spec, builds, showing, first_ordinal=len(shown) + 1)
    sources = {**reused.cited.sources, **rebuilt.sources}
    shown += [await _sent(spec, block, reused, showing, sources) for block in rebuilt.blocks]
    images = await pictures.sent(spec.id, stream, ordinal=len(shown) + 1)
    if images is not None:
        shown.append(images)
    await stream.section_done(spec.id, searched=None)
    return SectionOutcome(
        spec,
        blocks=tuple(shown),
        claim_ids=tuple(dict.fromkeys(claim for piece in reused.pieces for claim in piece.claim_ids)),
        sources=sources,
    )


async def _rebuilt(
    spec: SectionSpec, builds: SectionBuilds, showing: ReusedShowing, *, first_ordinal: int
) -> AddedBlocks:
    found = await builds.added(spec.id, first_ordinal=first_ordinal)
    return AddedBlocks(tuple(showing.enrichment.marked(block) for block in found.blocks), found.sources)


async def _sent(
    spec: SectionSpec,
    block: Block,
    reused: ReusedSection,
    showing: ReusedShowing,
    sources: Mapping[str, Mapping[str, Any]],
) -> Block:
    texts = {claim_id: view.text for claim_id, view in reused.cited.views.items()}
    translated = await block_in_language(
        block, stream=showing.stream, translation=showing.translation, claim_texts=texts
    )
    await showing.stream.blocks(spec.id, [translated], sources)
    return translated
