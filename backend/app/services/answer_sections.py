from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import TypeAdapter

from app.composer.candidates import compose_request, research_summary
from app.core.errors import AppError, spend_refusal
from app.research.composition import ComposedAnswer, ComposeFocus, ComposeRequest, searched_note
from app.research.evidence_pack import EvidencePack, ResearchTrail
from app.research.explainer import Block
from app.research.planning import PlanRequest, ResearchShare, RetrievalPlan
from app.research.sections import LADDER_DISCIPLINE, SectionSpec, block_id
from app.research.stream import ResearchProgress
from app.research.vocabulary import CANONICAL_LANGUAGE
from app.science.ladder import ladder_problems, ladder_stage_options, process_ladder
from app.science.records import ProcessRecords

from .answer_events import CitedClaims
from .answer_trail import stored_key
from .answer_translation import AnswerTranslation, translated_block, translated_sentences
from .block_builders import AddedBlocks, BlockBuilders, SectionBuilds
from .builder_interface import BuildAsk
from .explainer_events import ExplainerStream
from .research_ledger import ResearchLedger, may_research_fresh
from .section_blocks import (
    BlockRefused,
    KeptSentence,
    cited_sentence,
    kept_sentences,
    prose_block,
    section_sentences,
)
from .section_enrichment import Enrichment, PictureSearches

__all__ = [
    "SECTION_CONCURRENCY",
    "SECTION_STOPPED_NOTE",
    "SectionContext",
    "SectionOutcome",
    "SectionStore",
    "SectionTools",
    "block_in_language",
    "run_sections",
]

logger = logging.getLogger(__name__)

SECTION_CONCURRENCY = 4
SECTION_STOPPED_NOTE = "Research for this section stopped before a source could be read."
BLOCKS = TypeAdapter(Block)

ClaimsOf = tuple[tuple[uuid.UUID, ...], ...]


class SectionStore(Protocol):
    async def keep(self, answer_id: uuid.UUID, pack: EvidencePack, composed: ComposedAnswer) -> ClaimsOf: ...

    async def cited(self, claim_ids: Iterable[uuid.UUID]) -> CitedClaims: ...


@dataclass(frozen=True)
class SectionTools:
    research: Callable[[PlanRequest, ResearchProgress, ResearchTrail], Awaitable[EvidencePack]]
    compose: Callable[[ComposeRequest], Awaitable[ComposedAnswer]]
    store: SectionStore
    translation: AnswerTranslation


@dataclass(frozen=True)
class SectionContext:
    tools: SectionTools
    stream: ExplainerStream
    answer_id: uuid.UUID
    base: PlanRequest
    ledger: ResearchLedger
    enrichment: Enrichment
    process: ProcessRecords | None = None
    builders: BlockBuilders = field(default_factory=BlockBuilders)


@dataclass(frozen=True)
class SectionOutcome:
    spec: SectionSpec
    blocks: tuple[Block, ...] = ()
    built: tuple[Block, ...] = ()
    searched: str | None = None
    plans: tuple[RetrievalPlan, ...] = ()
    packs: tuple[EvidencePack, ...] = ()
    follow_ups: tuple[str, ...] = ()
    claim_ids: tuple[uuid.UUID, ...] = ()
    sources: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    failure: AppError | None = None


@dataclass(frozen=True)
class _Attempt:
    pack: EvidencePack
    composed: ComposedAnswer
    blocks: tuple[Block, ...]
    open_questions: tuple[dict[str, Any], ...]
    cited: CitedClaims
    evidence_ids: tuple[str, ...]
    claim_ids: tuple[uuid.UUID, ...] = field(default=())


async def run_sections(specs: Sequence[SectionSpec], context: SectionContext) -> list[SectionOutcome]:
    gate = asyncio.Semaphore(SECTION_CONCURRENCY)

    async def run(spec: SectionSpec, share: ResearchShare) -> SectionOutcome:
        async with gate:
            return await _guarded(spec, share, context)

    try:
        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(run(s, share))
                for s, share in zip(specs, context.ledger.shares, strict=True)
            ]
    except BaseExceptionGroup as failed:
        raise _first_failure(failed) from None
    return [task.result() for task in tasks]


async def _guarded(spec: SectionSpec, share: ResearchShare, context: SectionContext) -> SectionOutcome:
    try:
        return await _section(spec, share, context)
    except AppError as error:
        if spend_refusal(error):
            raise
        logger.warning("section %s stopped: %s", spec.id, error, exc_info=True)
        await context.stream.section_done(spec.id, searched=SECTION_STOPPED_NOTE)
        return SectionOutcome(spec, searched=SECTION_STOPPED_NOTE, failure=error)


async def _section(spec: SectionSpec, share: ResearchShare, context: SectionContext) -> SectionOutcome:
    attempts = [await _attempt(spec, context, context.ledger.take(share), fresh=False)]
    fresh = context.ledger.take_fresh(share) if _needs_fresh(attempts[0]) else None
    if fresh is not None:
        await context.stream.section_state(spec.id, "RESEARCHING")
        attempts.append(await _attempt(spec, context, fresh, fresh=True))
    shown = attempts[-1]
    async with context.enrichment.searching() as pictures, context.builders.building() as builds:
        pictures.start(spec.id, shown.blocks)
        builds.start(BuildAsk(context.answer_id, spec, context.base, shown.blocks, shown.cited))
        blocks, added = await _shown(spec, shown, context, pictures, builds)
    packs = tuple(attempt.pack for attempt in attempts)
    searched = None if blocks else searched_note(research_summary(*packs))
    sources = {**_sources(shown.cited, context.process), **added.sources}
    await context.stream.section_done(spec.id, searched=searched)
    await _quote_trail(shown, blocks, context, sources)
    return SectionOutcome(
        spec,
        blocks=blocks,
        built=(*shown.blocks, *added.blocks),
        searched=searched,
        plans=tuple(pack.plan for pack in packs),
        packs=packs,
        follow_ups=tuple(shown.composed.follow_ups),
        claim_ids=tuple(dict.fromkeys([*shown.claim_ids, *_claim_ids(added.blocks, ())])),
        sources=sources,
    )


async def _attempt(
    spec: SectionSpec, context: SectionContext, share: ResearchShare, *, fresh: bool
) -> _Attempt:
    pack = await _researched(spec, context, share, fresh=fresh)
    await context.stream.section_state(spec.id, "WRITING")
    request = compose_request(pack, context.base.question, focus=_focus(spec, context.process))
    if request.candidates:
        await context.stream.status("COMPOSING", len(request.candidates))
    composed = await context.tools.compose(request)
    await context.stream.section_state(spec.id, "CHECKING")
    claims_of = await _kept(context, pack, composed)
    cited = await context.tools.store.cited(claim for claims in claims_of for claim in claims)
    return _built(spec, context, pack, composed, sentences=kept_sentences(composed, claims_of), cited=cited)


async def _researched(
    spec: SectionSpec, context: SectionContext, share: ResearchShare, *, fresh: bool
) -> EvidencePack:
    request = PlanRequest.model_validate(
        context.base.model_dump() | {"focus": spec.discipline, "share": share.model_dump(), "fresh": fresh}
    )

    async def progress(step: Any, count: int) -> None:
        await context.stream.status(step, count)

    pack = await context.tools.research(request, progress, context.stream.trail)
    context.ledger.settle(share, pack)
    stored = await context.tools.store.cited(hit.claim_id for hit in pack.stored.claims)
    await context.stream.trail.found_stored(_stored_sources(pack, stored))
    return pack


async def _kept(context: SectionContext, pack: EvidencePack, composed: ComposedAnswer) -> ClaimsOf:
    if composed.not_enough_evidence is not None and not pack.documents:
        return ()
    if pack.documents:
        await context.stream.status("WRITING_BACK", len(pack.documents))
    return await context.tools.store.keep(context.answer_id, pack, composed)


def _built(
    spec: SectionSpec,
    context: SectionContext,
    pack: EvidencePack,
    composed: ComposedAnswer,
    *,
    sentences: Sequence[KeptSentence],
    cited: CitedClaims,
) -> _Attempt:
    split = section_sentences(sentences, cited)
    blocks: list[Block] = []
    ladder = _ladder(spec, context.process, composed, block_id(spec.id, 1))
    if ladder is not None:
        blocks.append(ladder)
    prose = _prose(block_id(spec.id, len(blocks) + 1), split.facts, cited)
    if prose is not None:
        blocks.append(prose)
    shown_facts = split.facts if prose is not None else ()
    open_questions = tuple(
        cited_sentence(f"{spec.id}.open.{n}", sentence, cited)
        for n, sentence in enumerate(split.open_questions, 1)
    )
    kept = (*shown_facts, *split.open_questions)
    return _Attempt(
        pack=pack,
        composed=composed,
        blocks=tuple(context.enrichment.marked(block) for block in blocks),
        open_questions=open_questions,
        cited=cited,
        evidence_ids=tuple(evidence for sentence in kept for evidence in sentence.evidence_ids),
        claim_ids=_claim_ids(blocks, open_questions),
    )


def _ladder(
    spec: SectionSpec, records: ProcessRecords | None, composed: ComposedAnswer, ladder_id: str
) -> Block | None:
    if records is None or spec.discipline != LADDER_DISCIPLINE or not composed.stage_ids:
        return None
    ladder = process_ladder(records, block_id=ladder_id, stage_ids=composed.stage_ids)
    if ladder is None:
        return None
    problems = ladder_problems(ladder, records)
    if problems:
        logger.warning("ladder %s refused: %s", ladder_id, "; ".join(problems))
        return None
    return ladder


def _prose(prose_id: str, facts: Sequence[KeptSentence], cited: CitedClaims) -> Block | None:
    if not facts:
        return None
    try:
        return prose_block(prose_id, facts, cited)
    except BlockRefused as refused:
        logger.warning("%s", refused)
        return None


async def _shown(
    spec: SectionSpec,
    attempt: _Attempt,
    context: SectionContext,
    pictures: PictureSearches,
    builds: SectionBuilds,
) -> tuple[tuple[Block, ...], AddedBlocks]:
    sources = _sources(attempt.cited, context.process)
    texts = _claim_texts(attempt.cited, context.process)
    shown: list[Block] = []
    for block in attempt.blocks:
        translated = await _in_language(block, context, texts)
        await context.stream.blocks(spec.id, [translated], sources)
        shown.append(translated)
    found = await builds.added(spec.id, first_ordinal=len(shown) + 1)
    added = AddedBlocks(tuple(context.enrichment.marked(block) for block in found.blocks), found.sources)
    for block in added.blocks:
        translated = await _in_language(block, context, texts)
        await context.stream.blocks(spec.id, [translated], {**sources, **added.sources})
        shown.append(translated)
    images = await pictures.sent(spec.id, context.stream, ordinal=len(shown) + 1)
    if images is not None:
        shown.append(images)
    open_questions = await _open_in_language(attempt.open_questions, context, texts)
    await context.stream.open_questions(open_questions, sources)
    return tuple(shown), added


async def _quote_trail(
    attempt: _Attempt,
    blocks: Sequence[Block],
    context: SectionContext,
    sources: Mapping[str, Mapping[str, Any]],
) -> None:
    trail = context.stream.trail
    ladder = {sid for block in blocks if block.kind == "process_ladder" for sid in block.cited_source_ids()}
    cited = dict.fromkeys(source_id for block in blocks for source_id in block.cited_source_ids())
    quoted = [sources[sid] for sid in cited if sid in ladder or trail.knows(stored_key(sid))]
    await trail.quoted(attempt.evidence_ids, quoted)


async def _in_language(block: Block, context: SectionContext, texts: Mapping[uuid.UUID, str]) -> Block:
    return await block_in_language(
        block, stream=context.stream, translation=context.tools.translation, claim_texts=texts
    )


async def block_in_language(
    block: Block,
    *,
    stream: ExplainerStream,
    translation: AnswerTranslation,
    claim_texts: Mapping[uuid.UUID, str],
) -> Block:
    if stream.language == CANONICAL_LANGUAGE:
        return block
    await stream.status("TRANSLATING")
    payload = block.model_dump(mode="json", by_alias=True, exclude_unset=True)
    shown = await translated_block(
        payload, language=stream.language, translation=translation, claim_texts=claim_texts
    )
    return BLOCKS.validate_python(shown)


async def _open_in_language(
    sentences: Sequence[dict[str, Any]], context: SectionContext, texts: Mapping[uuid.UUID, str]
) -> list[dict[str, Any]]:
    language = context.base.language
    if language == CANONICAL_LANGUAGE or not sentences:
        return list(sentences)
    await context.stream.status("TRANSLATING")
    return await translated_sentences(
        sentences, language=language, translation=context.tools.translation, claim_texts=texts
    )


def _focus(spec: SectionSpec, records: ProcessRecords | None) -> ComposeFocus:
    stages = ladder_stage_options(records) if records and spec.discipline == LADDER_DISCIPLINE else []
    return ComposeFocus(discipline=spec.discipline, title=spec.title, stages=stages)


def _needs_fresh(attempt: _Attempt) -> bool:
    return not attempt.blocks and may_research_fresh(attempt.pack)


def _stored_sources(pack: EvidencePack, stored: CitedClaims) -> list[Mapping[str, Any]]:
    ordered = dict.fromkeys(
        citation["sourceId"]
        for hit in pack.stored.claims
        if hit.claim_id in stored.views
        for citation in stored.views[hit.claim_id].citations
    )
    return [stored.sources[source_id] for source_id in ordered if source_id in stored.sources]


def _sources(cited: CitedClaims, records: ProcessRecords | None) -> dict[str, Mapping[str, Any]]:
    stored = {
        sid: ref.model_dump(mode="json", by_alias=True)
        for sid, ref in (records.sources if records else {}).items()
    }
    return {**stored, **cited.sources}


def _claim_texts(cited: CitedClaims, records: ProcessRecords | None) -> dict[uuid.UUID, str]:
    texts = {claim_id: claim.text for claim_id, claim in (records.claims if records else {}).items()}
    return texts | {claim_id: view.text for claim_id, view in cited.views.items()}


def _claim_ids(blocks: Sequence[Block], open_questions: Sequence[Mapping[str, Any]]) -> tuple[uuid.UUID, ...]:
    from_blocks = [citation.claim_id for block in blocks for citation in block.citations()]
    from_open = [citation["claimId"] for sentence in open_questions for citation in sentence["citations"]]
    return tuple(uuid.UUID(claim) for claim in dict.fromkeys([*from_blocks, *from_open]))


def _first_failure(group: BaseExceptionGroup) -> BaseException:
    leaves = list(_leaves(group))
    return next((leaf for leaf in leaves if isinstance(leaf, AppError)), leaves[0])


def _leaves(error: BaseException) -> Iterable[BaseException]:
    if isinstance(error, BaseExceptionGroup):
        for inner in error.exceptions:
            yield from _leaves(inner)
    else:
        yield error
