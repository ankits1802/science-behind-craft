from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from app.composer.candidates import research_summary
from app.core.errors import AppError, spend_refusal
from app.planner.policy import request_limits
from app.research.composition import (
    FOLLOW_UPS_MAX,
    ComposedAnswer,
    ComposeRequest,
    ResearchSummary,
    not_enough_evidence_message,
)
from app.research.crafts import CraftRef
from app.research.depth import depth_policy
from app.research.evidence_pack import EvidencePack, ResearchTrail
from app.research.explainer import Explainer
from app.research.explainer_versions import VersionMark
from app.research.planning import PlanRequest
from app.research.sections import LADDER_DISCIPLINE, AnswerPlans, SectionPlan, SectionSpec
from app.research.stream import Emit, ResearchProgress
from app.research.understanding import UnderstandAsk, Understanding, UnknownCraft
from app.research.vocabulary import CANONICAL_LANGUAGE
from app.science.records import ProcessRecords

from .answer_events import CitedClaims
from .answer_sections import (
    ClaimsOf,
    ResearchLedger,
    SectionContext,
    SectionOutcome,
    SectionTools,
    run_sections,
)
from .answer_translation import (
    AnswerTranslation,
    Segment,
    english_question,
    needs_english_rendering,
    translate_segments,
)
from .block_builders import BlockBuilders
from .explainer_document import explainer_document
from .explainer_events import ExplainerStream, status_message
from .explainer_history import STALE_VERSION_DETAIL, StaleVersion
from .follow_ups import AnswerLayout, FollowUp, answer_layout, understood_for
from .piece_lookup import PieceAsk
from .piece_store import BuiltSection, PieceStore
from .reused_sections import ReuseBuilds, ReusedShowing, reused_follow_ups, stream_reused
from .section_enrichment import Enrichment, EnrichmentTools
from .stored_explainer import stream_stored_answer

__all__ = [
    "NOT_FOUND_DETAIL",
    "RESEARCH_FAILED_DETAIL",
    "RESOLVER_FAILED_DETAIL",
    "STORED_ONLY_MODE",
    "UNEXPECTED_DETAIL",
    "AnswerAsk",
    "AnswerPipeline",
    "AnswerStore",
    "answer_question",
    "answer_understood",
    "status_message",
]

logger = logging.getLogger(__name__)

NOT_FOUND_DETAIL = "No craft has that address."
RESOLVER_FAILED_DETAIL = "Finding the craft failed just now. Try again."
RESEARCH_FAILED_DETAIL = "Research failed just now. Try again."
UNEXPECTED_DETAIL = "Something went wrong while answering. Try again."
STORED_ONLY_MODE = "VERIFIED"


@dataclass(frozen=True)
class AnswerAsk:
    question: str
    depth: str
    craft_slug: str | None = None
    any_craft: bool = False
    language: str | None = None
    user_id: uuid.UUID | None = None
    role: str | None = None
    withheld_terms: tuple[str, ...] = ()
    fresh: bool = False
    builds_on: FollowUp | None = None


class AnswerStore(Protocol):
    async def stored_claims(self, craft_slug: str, question: str, mode: str) -> CitedClaims: ...

    async def begin(self, ask: AnswerAsk, understanding: Understanding) -> uuid.UUID: ...

    async def keep(self, answer_id: uuid.UUID, pack: EvidencePack, composed: ComposedAnswer) -> ClaimsOf: ...

    async def cited(self, claim_ids: Iterable[uuid.UUID]) -> CitedClaims: ...

    async def process(self, craft_slug: str) -> ProcessRecords | None: ...

    async def finish(
        self,
        answer_id: uuid.UUID,
        *,
        plans: AnswerPlans,
        claim_ids: Sequence[uuid.UUID],
        explainer: Explainer | None,
        version: VersionMark | None = None,
    ) -> None: ...


@dataclass(frozen=True)
class AnswerPipeline:
    understand: Callable[[UnderstandAsk], Awaitable[Understanding]]
    research: Callable[[PlanRequest, ResearchProgress, ResearchTrail], Awaitable[EvidencePack]]
    compose: Callable[[ComposeRequest], Awaitable[ComposedAnswer]]
    store: AnswerStore
    translation: AnswerTranslation
    pieces: PieceStore
    enrichment: EnrichmentTools
    builders: BlockBuilders = field(default_factory=BlockBuilders)


@dataclass(frozen=True)
class _Run:
    ask: AnswerAsk
    understanding: Understanding
    pipeline: AnswerPipeline
    stream: ExplainerStream
    answer_id: uuid.UUID
    enrichment: Enrichment
    layout: AnswerLayout


async def answer_question(ask: AnswerAsk, pipeline: AnswerPipeline, emit: Emit) -> None:
    answer_id: uuid.UUID | None = None
    try:
        answer_id = await _answer(ask, pipeline, emit)
    except StaleVersion as stale:
        logger.warning("the follow-up was not kept: %s", stale)
        await emit("error", {"message": STALE_VERSION_DETAIL})
    except AppError as error:
        logger.warning("answering stopped: %s", error, exc_info=True)
        await emit("error", {"message": _user_message(error, RESEARCH_FAILED_DETAIL)})
    except Exception:
        logger.exception("answering failed")
        await emit("error", {"message": UNEXPECTED_DETAIL})
    await emit("done", {"answerId": str(answer_id) if answer_id else None})


async def answer_understood(
    ask: AnswerAsk, understanding: Understanding, pipeline: AnswerPipeline, emit: Emit
) -> uuid.UUID:
    return await _researched_answer(
        ask, understanding, pipeline, ExplainerStream(emit, language=_language(ask))
    )


async def _answer(ask: AnswerAsk, pipeline: AnswerPipeline, emit: Emit) -> uuid.UUID | None:
    understanding = await _understood(ask, pipeline, emit)
    if understanding is None:
        return None
    stream = ExplainerStream(emit, language=_language(ask))
    if understanding.refusal is not None:
        await _refused_answer(ask, understanding, pipeline, stream)
        return None
    return await _researched_answer(ask, understanding, pipeline, stream)


async def _understood(ask: AnswerAsk, pipeline: AnswerPipeline, emit: Emit) -> Understanding | None:
    request = UnderstandAsk(
        question=ask.question,
        depth=ask.depth,
        language=_language(ask),
        craft_slug=ask.craft_slug,
        any_craft=ask.any_craft,
        role=ask.role,
    )
    try:
        understanding = await pipeline.understand(request)
    except UnknownCraft:
        await emit("error", {"message": NOT_FOUND_DETAIL})
        return None
    except AppError as error:
        logger.warning("understanding the question failed", exc_info=True)
        await emit("error", {"message": _user_message(error, RESOLVER_FAILED_DETAIL)})
        return None
    await emit("understood", understood_for(understanding, ask.builds_on))
    if ask.builds_on is not None:
        await emit("builds_on", ask.builds_on.event())
    return understanding


async def _refused_answer(
    ask: AnswerAsk, understanding: Understanding, pipeline: AnswerPipeline, stream: ExplainerStream
) -> None:
    if understanding.craft is None or ask.builds_on is not None:
        await stream.emit("error", {"message": understanding.refusal})
        return
    await _stored_answer(ask, understanding.craft, pipeline, stream)


async def _stored_answer(
    ask: AnswerAsk, craft: CraftRef, pipeline: AnswerPipeline, stream: ExplainerStream
) -> None:
    await stream.status("SEARCHING_STORED")
    question = await english_question(ask.question, pipeline.translation)
    cited = await pipeline.store.stored_claims(craft.slug, question, STORED_ONLY_MODE)
    if await stream_stored_answer(stream, craft.name, cited, translation=pipeline.translation):
        return
    summary = ResearchSummary(
        craft=craft,
        mode=STORED_ONLY_MODE,
        stored_claims=0,
        stored_passages=0,
        evidence_found=0,
        documents_read=0,
        failures=0,
    )
    await stream.emit("not_enough_evidence", {"message": not_enough_evidence_message(summary)})


async def _researched_answer(
    ask: AnswerAsk, understanding: Understanding, pipeline: AnswerPipeline, stream: ExplainerStream
) -> uuid.UUID:
    craft = understanding.craft
    await stream.status("PLANNING", craft=craft.name if craft else "")
    layout = answer_layout(understanding, ask.builds_on)
    specs = layout.specs
    answer_id = await pipeline.store.begin(ask, understanding)
    titles = {
        **await _translated(_title_segments(layout.untitled), stream.language, pipeline.translation),
        **layout.titles,
    }
    lookup = await pipeline.pieces.reusable(_piece_ask(ask, understanding, layout.reusable))
    enrichment = await pipeline.enrichment.for_answer(craft)
    run = _Run(ask, understanding, pipeline, stream, answer_id, enrichment, layout)
    reused = await stream_reused(specs, lookup, _reused_showing(run, titles))
    open_specs = [spec for spec in specs if spec.discipline not in lookup.reused]
    for spec in open_specs:
        await stream.section_started(spec, titles=titles, state="RESEARCHING")
    researched = await _research(open_specs, run)
    outcomes = sorted([*reused, *researched], key=lambda outcome: outcome.spec.order)
    english = _english_follow_ups(outcomes) if open_specs else reused_follow_ups(craft, lookup)
    follow_ups = await _closing(outcomes, english, stream, pipeline.translation)
    await _finish(run, outcomes, titles=titles, follow_ups=follow_ups)
    built = [
        BuiltSection(
            outcome.spec.discipline, outcome.built, deepened=not layout.keeps_pieces_of(outcome.spec)
        )
        for outcome in researched
        if outcome.built
    ]
    await pipeline.pieces.keep(lookup, answer_id=answer_id, depth=understanding.depth, sections=built)
    return answer_id


def _reused_showing(run: _Run, titles: Mapping[str, str]) -> ReusedShowing:
    builds = ReuseBuilds(
        run.pipeline.builders.for_reuse(), run.answer_id, _plan_request(run.ask, run.understanding)
    )
    return ReusedShowing(run.stream, titles, run.pipeline.translation, run.enrichment, builds)


async def _research(specs: Sequence[SectionSpec], run: _Run) -> list[SectionOutcome]:
    if not specs:
        return []
    pipeline = run.pipeline
    base = _plan_request(run.ask, run.understanding)
    context = SectionContext(
        tools=SectionTools(pipeline.research, pipeline.compose, pipeline.store, pipeline.translation),
        stream=run.stream,
        answer_id=run.answer_id,
        base=base,
        ledger=ResearchLedger(request_limits(base, base.mode), len(specs)),
        enrichment=run.enrichment,
        process=await _process(run.understanding.craft, specs, pipeline.store),
        builders=pipeline.builders,
        deepening=run.layout.deepening,
    )
    return await run_sections(specs, context)


async def _finish(
    run: _Run, outcomes: Sequence[SectionOutcome], *, titles: Mapping[str, str], follow_ups: Sequence[str]
) -> None:
    document = explainer_document(
        answer_id=run.answer_id,
        question=run.ask.question,
        understood=run.layout.understood(run.understanding),
        outcomes=outcomes,
        titles=titles,
        follow_ups=follow_ups,
    )
    stored = run.layout.stored(document, dict.fromkeys(c for outcome in outcomes for c in outcome.claim_ids))
    await run.pipeline.store.finish(
        run.answer_id,
        plans=_plans(outcomes),
        claim_ids=list(stored.claim_ids),
        explainer=stored.explainer,
        version=stored.version,
    )
    if stored.version is not None:
        await run.stream.emit("version", stored.version)


def _piece_ask(ask: AnswerAsk, understanding: Understanding, specs: Sequence[SectionSpec]) -> PieceAsk:
    return PieceAsk(
        question=ask.question,
        craft=understanding.craft,
        facets=tuple(spec.discipline for spec in specs),
        depth=understanding.depth,
        fresh=ask.fresh,
    )


def _english_follow_ups(outcomes: Sequence[SectionOutcome]) -> list[str]:
    return list(dict.fromkeys(item for outcome in outcomes for item in outcome.follow_ups))


async def _closing(
    outcomes: Sequence[SectionOutcome],
    offered: Sequence[str],
    stream: ExplainerStream,
    translation: AnswerTranslation,
) -> list[str]:
    if any(outcome.blocks for outcome in outcomes):
        english = list(offered)[:FOLLOW_UPS_MAX]
        found = await _translated(
            [Segment(f"follow-up:{n}", item) for n, item in enumerate(english)], stream.language, translation
        )
        follow_ups = [found.get(f"follow-up:{n}", item) for n, item in enumerate(english)]
        await stream.emit("follow_ups", {"items": follow_ups})
        return follow_ups
    failures = [outcome.failure for outcome in outcomes if outcome.failure is not None]
    if len(failures) == len(outcomes):
        raise failures[0]
    packs = [pack for outcome in outcomes for pack in outcome.packs]
    message = not_enough_evidence_message(research_summary(*packs))
    await stream.emit("not_enough_evidence", {"message": message})
    return []


async def _process(
    craft: CraftRef | None, specs: Sequence[SectionSpec], store: AnswerStore
) -> ProcessRecords | None:
    if craft is None or all(spec.discipline != LADDER_DISCIPLINE for spec in specs):
        return None
    return await store.process(craft.slug)


async def _translated(
    segments: Sequence[Segment], language: str, translation: AnswerTranslation
) -> dict[str, str]:
    if language == CANONICAL_LANGUAGE or not segments:
        return {}
    return await translate_segments(segments, language=language, translation=translation)


def _title_segments(specs: Sequence[SectionSpec]) -> list[Segment]:
    return [Segment(spec.id, spec.title) for spec in specs]


def _plans(outcomes: Sequence[SectionOutcome]) -> AnswerPlans:
    return AnswerPlans(
        sections=[
            SectionPlan(section_id=outcome.spec.id, discipline=outcome.spec.discipline, plan=plan)
            for outcome in outcomes
            for plan in outcome.plans
        ]
    )


def _plan_request(ask: AnswerAsk, understanding: Understanding) -> PlanRequest:
    return PlanRequest(
        question=ask.question,
        mode=depth_policy(understanding.depth).mode,
        craft=understanding.craft,
        compared=tuple(understanding.compared),
        depth=understanding.depth,
        language=_language(ask),
        withheld_terms=ask.withheld_terms,
        english_question=None if needs_english_rendering(ask.question) else ask.question,
        seats=tuple(understanding.seats),
    )


def _language(ask: AnswerAsk) -> str:
    return ask.language or CANONICAL_LANGUAGE


def _user_message(error: AppError, otherwise: str) -> str:
    return spend_refusal(error) or otherwise
