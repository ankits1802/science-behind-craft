from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import partial
from typing import Any

from app.research.explainer import Block
from app.research.knowledge_pieces import placed_block
from app.research.planning import PlanRequest
from app.research.sections import SectionSpec, block_id

from .answer_lede import Opening
from .answer_sections import SectionOutcome
from .answer_translation import AnswerTranslation
from .block_builders import AddedBlocks, BlockBuilders, SectionBuilds
from .builder_interface import BuildAsk
from .claim_ledger import COVERED_NOTE, admission_batches
from .explainer_events import ExplainerStream, shown_title
from .piece_lookup import PieceLookup, ReusedSection
from .section_enrichment import Enrichment, PictureSearches
from .section_headings import Headed, headed_specs, heading_supports
from .section_language import block_in_language

__all__ = ["REUSED_SECTION_STATE", "ReuseBuilds", "ReusedShowing", "stream_reused", "stream_reused_beside"]

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
    opening: Awaitable[Opening] | None = None


async def stream_reused(
    specs: Sequence[SectionSpec], lookup: PieceLookup, showing: ReusedShowing
) -> list[SectionOutcome]:
    chosen = [
        (spec, lookup.reused[spec.discipline])
        for spec in sorted(specs, key=lambda spec: spec.order)
        if spec.discipline in lookup.reused
    ]
    placed = {spec.id: _placed(spec, reused) for spec, reused in chosen}
    headed = await _headed(chosen, placed, showing)
    shown = replace(showing, titles={**showing.titles, **{h.spec.id: h.shown for h in headed if h.shown}})
    async with showing.enrichment.searching() as pictures:
        return [
            replace(
                await _reused_section(h.spec, reused, placed[h.spec.id], shown, pictures), shown_title=h.shown
            )
            for h, (_, reused) in zip(headed, chosen, strict=True)
        ]


async def stream_reused_beside(
    specs: Sequence[SectionSpec],
    lookup: PieceLookup,
    showing: ReusedShowing,
    research: Awaitable[list[SectionOutcome]],
) -> tuple[list[SectionOutcome], list[SectionOutcome]]:
    researching = asyncio.ensure_future(research)
    try:
        reused = await stream_reused(specs, lookup, showing)
        return reused, await researching
    finally:
        researching.cancel()
        await asyncio.gather(researching, return_exceptions=True)


async def _headed(
    chosen: Sequence[tuple[SectionSpec, ReusedSection]],
    placed: Mapping[str, Sequence[Block]],
    showing: ReusedShowing,
) -> list[Headed]:
    if showing.opening is None or not chosen:
        return [Headed(spec) for spec, _ in chosen]
    opened = await showing.opening
    shown = [(spec, heading_supports(placed[spec.id], reused.cited)) for spec, reused in chosen]
    language = showing.stream.language
    return await headed_specs(opened.headings, shown, language=language, translation=showing.translation)


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
        shown: list[Block] = []
        for batch in admission_batches(placed):
            shown += await _sent(spec, batch, reused, showing, reused.cited.sources)
        pictures.start(spec.id, shown)
        rebuilt = await _rebuilt(spec, builds, showing, first_ordinal=len(placed) + 1)
    sources = {**reused.cited.sources, **rebuilt.sources}
    shown += await _sent(spec, rebuilt.blocks, reused, showing, sources)
    images = await pictures.sent(spec.id, stream, ordinal=len(placed) + len(rebuilt.blocks) + 1)
    if images is not None:
        shown.append(images)
    searched = None if shown else COVERED_NOTE
    await stream.section_done(spec.id, searched=searched)
    return SectionOutcome(
        spec,
        blocks=tuple(shown),
        searched=searched,
        claim_ids=tuple(dict.fromkeys(claim for piece in reused.pieces for claim in piece.claim_ids)),
        sources={**sources, **stream.shown_sources()},
    )


async def _rebuilt(
    spec: SectionSpec, builds: SectionBuilds, showing: ReusedShowing, *, first_ordinal: int
) -> AddedBlocks:
    found = await builds.added(spec.id, first_ordinal=first_ordinal)
    return AddedBlocks(tuple(showing.enrichment.marked(block) for block in found.blocks), found.sources)


async def _sent(
    spec: SectionSpec,
    blocks: Sequence[Block],
    reused: ReusedSection,
    showing: ReusedShowing,
    sources: Mapping[str, Mapping[str, Any]],
) -> list[Block]:
    texts = {claim_id: view.text for claim_id, view in reused.cited.views.items()}
    in_language = partial(
        block_in_language, stream=showing.stream, translation=showing.translation, claim_texts=texts
    )
    return await showing.stream.blocks(spec.id, blocks, sources, in_language=in_language)
