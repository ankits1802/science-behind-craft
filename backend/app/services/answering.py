from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

from app.composer.candidates import compose_request, research_summary
from app.core.errors import AppError
from app.research.composition import (
    ComposedAnswer,
    ComposeRequest,
    ResearchSummary,
    not_enough_evidence_message,
)
from app.research.crafts import CraftQuery, CraftRef, CraftResolution
from app.research.evidence_pack import EvidencePack
from app.research.planning import PlanRequest
from app.research.stream import Emit, ResearchProgress, StatusStep, match_event
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS, CANONICAL_LANGUAGE

from .answer_events import CitedClaims, StreamEvent, composed_answer_events, stored_answer_events
from .answer_translation import (
    AnswerTranslation,
    english_question,
    needs_english_rendering,
    translated_composed_events,
    translated_stored_events,
)

__all__ = [
    "NOT_FOUND_DETAIL",
    "NO_CRAFT_DETAIL",
    "RESEARCH_FAILED_DETAIL",
    "RESOLVER_FAILED_DETAIL",
    "UNEXPECTED_DETAIL",
    "AnswerAsk",
    "AnswerPipeline",
    "AnswerStore",
    "KeptAnswer",
    "answer_question",
    "status_message",
]

logger = logging.getLogger(__name__)

NOT_FOUND_DETAIL = "No craft has that address."
NO_CRAFT_DETAIL = "Name the craft you are asking about, or open it from the craft list."
RESOLVER_FAILED_DETAIL = "Finding the craft failed just now. Name it exactly, or open it from the craft list."
RESEARCH_FAILED_DETAIL = "Research failed just now. Try again, or ask in Verified mode."
UNEXPECTED_DETAIL = "Something went wrong while answering. Try again."
BUDGET_REFUSAL_KINDS = frozenset({"ceiling"})


@dataclass(frozen=True)
class AnswerAsk:
    question: str
    mode: str
    craft_slug: str | None = None
    language: str | None = None
    user_id: uuid.UUID | None = None
    withheld_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class KeptAnswer:
    answer_id: uuid.UUID
    claims_of: tuple[tuple[uuid.UUID, ...], ...]


class AnswerStore(Protocol):
    async def stored_claims(self, craft_slug: str, question: str, mode: str) -> CitedClaims: ...

    async def keep(self, ask: AnswerAsk, pack: EvidencePack, answer: ComposedAnswer) -> KeptAnswer: ...

    async def cited(self, claim_ids: Iterable[uuid.UUID]) -> CitedClaims: ...


@dataclass(frozen=True)
class AnswerPipeline:
    resolve: Callable[[CraftQuery], Awaitable[CraftResolution]]
    research: Callable[[PlanRequest, ResearchProgress], Awaitable[EvidencePack]]
    compose: Callable[[ComposeRequest], Awaitable[ComposedAnswer]]
    store: AnswerStore
    translation: AnswerTranslation


def status_message(step: StatusStep, count: int = 0, craft: str = "", *, language: str = "") -> str:
    messages = {
        "RESOLVING": "Finding the craft",
        "PLANNING": f"Planning the research on {craft}",
        "SEARCHING_STORED": "Searching stored findings",
        "RESEARCHING": f"Searching {_counted(count, 'live query', 'live queries')}",
        "READING": f"Reading the best of {_counted(count, 'source', 'sources')} found",
        "COMPOSING": f"Writing a cited answer from {_counted(count, 'passage', 'passages')}",
        "WRITING_BACK": f"Saving {_counted(count, 'source', 'sources')} for the next question",
        "TRANSLATING": f"Translating the answer into {language}",
    }
    return messages[step]


async def answer_question(ask: AnswerAsk, pipeline: AnswerPipeline, emit: Emit) -> None:
    answer_id: uuid.UUID | None = None
    try:
        answer_id = await _answer(ask, pipeline, emit)
    except AppError as error:
        logger.warning("answering stopped: %s", error, exc_info=True)
        await emit("error", {"message": _user_message(error, RESEARCH_FAILED_DETAIL)})
    except Exception:
        logger.exception("answering failed")
        await emit("error", {"message": UNEXPECTED_DETAIL})
    await emit("done", {"answerId": str(answer_id) if answer_id else None})


async def _answer(ask: AnswerAsk, pipeline: AnswerPipeline, emit: Emit) -> uuid.UUID | None:
    await _status(emit, "RESOLVING")
    craft = await _resolved_craft(ask, pipeline, emit)
    if craft is None:
        return None
    if ask.mode == "VERIFIED":
        await _stored_answer(ask, craft, pipeline, emit)
        return None
    return await _researched_answer(ask, craft, pipeline, emit)


async def _resolved_craft(ask: AnswerAsk, pipeline: AnswerPipeline, emit: Emit) -> CraftRef | None:
    query = CraftQuery(text=ask.question, craft_slug=ask.craft_slug, language=ask.language)
    try:
        resolution = await pipeline.resolve(query)
    except AppError as error:
        logger.warning("craft resolution failed", exc_info=True)
        await emit("error", {"message": _user_message(error, RESOLVER_FAILED_DETAIL)})
        return None
    if ask.craft_slug and resolution.status != "RESOLVED":
        await emit("error", {"message": NOT_FOUND_DETAIL})
        return None
    await emit("match", match_event(resolution))
    if resolution.status == "RESOLVED" and resolution.craft is not None:
        return resolution.craft
    if resolution.status == "NONE":
        await emit("error", {"message": NO_CRAFT_DETAIL})
    return None


async def _stored_answer(ask: AnswerAsk, craft: CraftRef, pipeline: AnswerPipeline, emit: Emit) -> None:
    await _status(emit, "SEARCHING_STORED")
    question = await english_question(ask.question, pipeline.translation)
    cited = await pipeline.store.stored_claims(craft.slug, question, ask.mode)
    events = stored_answer_events(craft.name, cited)
    if events and _language(ask) != CANONICAL_LANGUAGE:
        await _translating(emit, ask)
        events = await translated_stored_events(
            events, language=_language(ask), translation=pipeline.translation, claim_texts=_texts(cited)
        )
    if not events:
        summary = ResearchSummary(
            craft=craft,
            mode=ask.mode,
            stored_claims=0,
            stored_passages=0,
            evidence_found=0,
            documents_read=0,
            failures=0,
        )
        await emit("not_enough_evidence", {"message": not_enough_evidence_message(summary)})
        return
    await _emit_all(emit, events)


async def _researched_answer(
    ask: AnswerAsk, craft: CraftRef, pipeline: AnswerPipeline, emit: Emit
) -> uuid.UUID:
    await _status(emit, "PLANNING", craft=craft.name)
    request = PlanRequest(
        question=ask.question,
        mode=ask.mode,
        craft=craft,
        language=_language(ask),
        withheld_terms=ask.withheld_terms,
        english_question=None if needs_english_rendering(ask.question) else ask.question,
    )

    async def progress(step: StatusStep, count: int) -> None:
        await _status(emit, step, count)

    pack = await pipeline.research(request, progress)
    composing = compose_request(pack, ask.question)
    if composing.candidates:
        await _status(emit, "COMPOSING", len(composing.candidates))
    composed = await pipeline.compose(composing)
    if pack.documents:
        await _status(emit, "WRITING_BACK", len(pack.documents))
    kept = await pipeline.store.keep(ask, pack, composed)
    events: list[StreamEvent] = []
    if composed.not_enough_evidence is None:
        cited = await pipeline.store.cited(claim for claims in kept.claims_of for claim in claims)
        events = composed_answer_events(composed, kept.claims_of, cited)
        if events and _language(ask) != CANONICAL_LANGUAGE:
            await _translating(emit, ask)
            events = await translated_composed_events(
                events, language=_language(ask), translation=pipeline.translation, claim_texts=_texts(cited)
            )
    if not events:
        summary = composed.not_enough_evidence or research_summary(pack)
        await emit("not_enough_evidence", {"message": not_enough_evidence_message(summary)})
    await _emit_all(emit, events)
    return kept.answer_id


async def _emit_all(emit: Emit, events: list[StreamEvent]) -> None:
    for name, payload in events:
        await emit(name, payload)


async def _status(emit: Emit, step: StatusStep, count: int = 0, *, craft: str = "") -> None:
    await emit("status", {"step": step, "message": status_message(step, count, craft)})


async def _translating(emit: Emit, ask: AnswerAsk) -> None:
    label = ANSWER_LANGUAGE_SPECS[_language(ask)].label
    await emit("status", {"step": "TRANSLATING", "message": status_message("TRANSLATING", language=label)})


def _language(ask: AnswerAsk) -> str:
    return ask.language or CANONICAL_LANGUAGE


def _texts(cited: CitedClaims) -> dict[uuid.UUID, str]:
    return {claim_id: view.text for claim_id, view in cited.views.items()}


def _user_message(error: AppError, otherwise: str) -> str:
    if getattr(error, "kind", None) in BUDGET_REFUSAL_KINDS and str(error):
        return str(error)
    return otherwise


def _counted(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"
