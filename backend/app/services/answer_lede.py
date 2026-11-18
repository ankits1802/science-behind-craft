from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field, replace
from functools import partial
from typing import Any, Protocol

from app.core.errors import AppError
from app.research.blocks_lede import LedeBlock
from app.research.composition import ComposeCandidate, ComposedLede, LedeRequest, LedeSection
from app.research.crafts import CraftRef
from app.research.depth import depth_policy
from app.research.planning import OPEN_QUESTION_LEVEL
from app.research.sections import SectionSpec
from app.research.understanding import Understanding
from app.research.vocabulary import CANONICAL_LANGUAGE, LEVEL_ORDER

from .answer_events import CitedClaims
from .answer_sections import SectionOutcome
from .answer_translation import AnswerTranslation, english_question, translated_block
from .claim_ledger import sentence_keys
from .explainer_events import ExplainerStream
from .knowledge_view import ClaimView
from .piece_lookup import PieceLookup, ReusedSection
from .section_blocks import BlockRefused, KeptSentence, lede_block
from .section_enrichment import Enrichment

__all__ = [
    "HEADING_CLAIMS_MAX",
    "LEDE_CLAIMS_MAX",
    "LEDE_WAIT_SECONDS",
    "AnswerOpening",
    "LedeAsk",
    "LedePlan",
    "LedeTools",
    "LedeWriting",
    "Opening",
    "OpeningStore",
    "SectionToHead",
    "SectionsShown",
    "early_opening",
    "evidence_for",
    "late_opening",
    "lede_plan",
    "opening_lede",
    "sections_shown",
    "written_opening",
]

logger = logging.getLogger(__name__)

LEDE_CLAIMS_MAX = 16
HEADING_CLAIMS_MAX = 8
LEDE_WAIT_SECONDS = 30.0
LABEL_MAX_CHARS = 300

ComposeLede = Callable[[LedeRequest], Awaitable[ComposedLede]]
StoredClaims = Callable[[str, str, str], Awaitable[CitedClaims]]
CitedOf = Callable[[Iterable[uuid.UUID]], Awaitable[CitedClaims]]


class OpeningStore(Protocol):
    async def stored_claims(self, craft_slug: str, question: str, mode: str) -> CitedClaims: ...

    async def cited(self, claim_ids: Iterable[uuid.UUID]) -> CitedClaims: ...


@dataclass(frozen=True)
class LedeTools:
    compose: ComposeLede | None = None
    wait_seconds: float = LEDE_WAIT_SECONDS


@dataclass(frozen=True)
class SectionToHead:
    section_id: str
    discipline: str
    claim_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class LedeAsk:
    question: str
    english: str
    craft: CraftRef | None
    evidence: CitedClaims
    sections: tuple[SectionToHead, ...] = ()
    said: frozenset[str] = frozenset()


@dataclass(frozen=True)
class LedePlan:
    question: str
    craft: CraftRef | None
    mode: str
    heads: tuple[SectionToHead, ...] = ()
    reused: CitedClaims = field(default_factory=CitedClaims)
    english: str = ""


@dataclass(frozen=True)
class Opening:
    lede: LedeBlock | None = None
    headings: Mapping[str, str] = field(default_factory=dict)
    follow_ups: tuple[str, ...] = ()
    sources: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    english: str = ""
    deferred: bool = False

    def asked(self, question: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(form for form in (question, self.english) if form))


@dataclass(frozen=True)
class SectionsShown:
    claim_ids: tuple[uuid.UUID, ...] = ()
    said: frozenset[str] = frozenset()


@dataclass(frozen=True)
class LedeWriting:
    stream: ExplainerStream
    translation: AnswerTranslation
    enrichment: Enrichment


@dataclass(frozen=True)
class AnswerOpening:
    plan: LedePlan
    tools: LedeTools
    writing: LedeWriting
    store: OpeningStore

    def started(self) -> AbstractAsyncContextManager[asyncio.Task[Opening]]:
        written = partial(early_opening, self.plan, self.tools, self.writing, self.store.stored_claims)
        return opening_lede(self.writing.stream, written, wait_seconds=self.tools.wait_seconds)

    async def settled(self, first: Opening, outcomes: Sequence[SectionOutcome]) -> Opening:
        if first.lede is not None or not first.deferred:
            return first
        plan = replace(self.plan, english=first.english)
        shown = sections_shown(outcomes)
        written = partial(late_opening, plan, self.tools, self.writing, self.store.cited, shown)
        late = await _softly(written, self.tools.wait_seconds)
        return late if late.lede is not None else first


@asynccontextmanager
async def opening_lede(
    stream: ExplainerStream,
    written: Callable[[], Awaitable[Opening]],
    *,
    wait_seconds: float = LEDE_WAIT_SECONDS,
) -> AsyncIterator[asyncio.Task[Opening]]:
    stream.hold_blocks_for_lede()
    task = asyncio.create_task(_sent_first(stream, written, wait_seconds))
    try:
        yield task
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        stream.release_blocks()


def lede_plan(
    question: str, understanding: Understanding, untitled: Sequence[SectionSpec], lookup: PieceLookup
) -> LedePlan:
    reused = [(spec, lookup.reused[spec.discipline]) for spec in untitled if spec.discipline in lookup.reused]
    heads = tuple(
        SectionToHead(spec.id, spec.discipline, _claims_in_reading_order(section)) for spec, section in reused
    )
    mode = depth_policy(understanding.depth).mode
    cited = evidence_for(*(section.cited for _, section in reused))
    return LedePlan(question, understanding.craft, mode, heads, cited)


async def early_opening(
    plan: LedePlan, tools: LedeTools, writing: LedeWriting, stored: StoredClaims
) -> Opening:
    if tools.compose is None:
        return Opening()
    english = await _english(plan, writing)
    found = await stored(plan.craft.slug, english, plan.mode) if plan.craft else CitedClaims()
    ask = LedeAsk(plan.question, english, plan.craft, evidence_for(found, plan.reused), plan.heads)
    return await written_opening(ask, tools, writing)


async def late_opening(
    plan: LedePlan, tools: LedeTools, writing: LedeWriting, cited: CitedOf, shown: SectionsShown
) -> Opening:
    if tools.compose is None or not shown.claim_ids:
        return Opening()
    english = await _english(plan, writing)
    ask = LedeAsk(plan.question, english, plan.craft, await cited(shown.claim_ids), said=shown.said)
    opening = await written_opening(ask, tools, writing)
    if opening.lede is not None:
        await writing.stream.lede(opening.lede, opening.sources)
    return opening


async def written_opening(ask: LedeAsk, tools: LedeTools, writing: LedeWriting) -> Opening:
    if tools.compose is None:
        return Opening(english=ask.english)
    request = _lede_request(ask)
    if not request.candidates:
        return Opening(english=ask.english, deferred=True)
    try:
        composed = await tools.compose(request)
    except AppError as error:
        logger.warning("the lede was not written: %s", error)
        return Opening(english=ask.english)
    return Opening(
        lede=await _shown_lede(ask, composed, writing),
        headings=dict(composed.headings),
        follow_ups=tuple(composed.follow_ups),
        sources=ask.evidence.sources,
        english=ask.english,
    )


def sections_shown(outcomes: Sequence[SectionOutcome]) -> SectionsShown:
    sentences = [s for outcome in outcomes for block in outcome.blocks for s in block.cited_sentences()]
    return SectionsShown(
        claim_ids=tuple(dict.fromkeys(claim for outcome in outcomes for claim in outcome.claim_ids)),
        said=frozenset(key for s in sentences for key in sentence_keys(s.text, s.original)),
    )


async def _english(plan: LedePlan, writing: LedeWriting) -> str:
    return plan.english or await english_question(plan.question, writing.translation)


async def _sent_first(
    stream: ExplainerStream, written: Callable[[], Awaitable[Opening]], wait_seconds: float
) -> Opening:
    try:
        opening = await _softly(written, wait_seconds)
        if opening.lede is not None:
            await stream.lede(opening.lede, opening.sources)
        return opening
    finally:
        stream.release_blocks()


async def _softly(written: Callable[[], Awaitable[Opening]], wait_seconds: float) -> Opening:
    try:
        async with asyncio.timeout(wait_seconds):
            return await written()
    except asyncio.CancelledError:
        raise
    except TimeoutError:
        logger.warning("the lede took longer than %s s; the answer opens with its sections", wait_seconds)
        return Opening()
    except Exception:
        logger.warning("the lede failed; the answer opens with its sections", exc_info=True)
        return Opening()


def _lede_request(ask: LedeAsk) -> LedeRequest:
    views = _offered_views(ask)
    shown = {view.id for view in views}
    sections = [
        LedeSection(
            section_id=section.section_id,
            discipline=section.discipline,
            claim_ids=[str(claim) for claim in section.claim_ids if claim in shown],
        )
        for section in ask.sections
        if any(claim in shown for claim in section.claim_ids)
    ]
    return LedeRequest(
        question=ask.english,
        craft=ask.craft,
        candidates=[_candidate(view) for view in views],
        sections=sections,
    )


def _offered_views(ask: LedeAsk) -> list[ClaimView]:
    facts = {
        claim_id: view for claim_id, view in ask.evidence.views.items() if view.level != OPEN_QUESTION_LEVEL
    }
    ranked = sorted(facts.values(), key=lambda view: (-view.rank, LEVEL_ORDER.get(view.level, 9)))
    heading_claims = [
        claim
        for section in ask.sections
        for claim in section.claim_ids[:HEADING_CLAIMS_MAX]
        if claim in facts
    ]
    chosen = dict.fromkeys([*(view.id for view in ranked[:LEDE_CLAIMS_MAX]), *heading_claims])
    return [facts[claim_id] for claim_id in chosen]


def _candidate(view: ClaimView) -> ComposeCandidate:
    quotes = list(dict.fromkeys(c["quote"] for c in view.citations if c.get("quote")))
    return ComposeCandidate(
        id=str(view.id),
        kind="CLAIM",
        text=view.text,
        quotes=quotes,
        source_label=f"stored claim, {view.level.lower()}"[:LABEL_MAX_CHARS],
        level=view.level,
    )


async def _shown_lede(ask: LedeAsk, composed: ComposedLede, writing: LedeWriting) -> LedeBlock | None:
    kept = [
        KeptSentence(s.text, tuple(s.claim_ids), tuple(s.evidence_ids), False)
        for s in composed.sentences
        if not sentence_keys(s.text) & ask.said
    ]
    try:
        lede = lede_block(ask.question, kept, ask.evidence)
    except BlockRefused as refused:
        logger.warning("%s", refused)
        return None
    marked = writing.enrichment.marked(lede)
    if writing.stream.language == CANONICAL_LANGUAGE:
        return marked
    await writing.stream.status("TRANSLATING")
    texts = {claim_id: view.text for claim_id, view in ask.evidence.views.items()}
    payload = marked.model_dump(mode="json", by_alias=True)
    shown = await translated_block(
        payload, language=writing.stream.language, translation=writing.translation, claim_texts=texts
    )
    return LedeBlock.model_validate(shown)


def evidence_for(*found: CitedClaims) -> CitedClaims:
    views = {claim_id: view for cited in found for claim_id, view in cited.views.items()}
    sources = {source_id: ref for cited in found for source_id, ref in cited.sources.items()}
    return CitedClaims(views=views, sources=sources)


def _claims_in_reading_order(section: ReusedSection) -> tuple[uuid.UUID, ...]:
    cited = (citation.claim_id for piece in section.pieces for citation in piece.payload.citations())
    return tuple(uuid.UUID(claim) for claim in dict.fromkeys(cited))
