from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.research.candidate_gates import (
    DUPLICATE_GATE,
    NOVELTY_GATE,
    Candidate,
    CitedSource,
    FactComparison,
    GateOutcome,
    HeldFact,
    NoveltyVerdict,
    close_facts,
    duplicate_outcome,
    held_twin,
    novelty_outcome,
    quote_gate,
    source_gate,
)
from app.research.candidate_judge import (
    JudgeAsk,
    JudgeRequest,
    comparison_request,
    novelty_request,
    parsed_comparisons,
    parsed_novelty,
)
from app.research.embedding import TextEmbedder, checked_vectors
from app.research.structured import StructuredModel, reply_object
from app.retrieval.text import document_text

__all__ = [
    "NOVELTY_FACTS_MAX",
    "GateRun",
    "HeldFacts",
    "LaterGates",
    "first_gates",
    "gate_run",
    "later_gates",
]

NOVELTY_FACTS_MAX = 12


class HeldFacts(Protocol):
    async def nearest(self, field: str | None, vector: Sequence[float], limit: int) -> list[HeldFact]: ...

    async def twins(self, field: str | None, statement: str) -> list[HeldFact]: ...


@dataclass(frozen=True)
class LaterGates:
    outcomes: tuple[GateOutcome, ...]
    vector: list[float] | None


@dataclass(frozen=True)
class GateRun:
    candidate: Candidate
    outcomes: tuple[GateOutcome, ...]
    vector: list[float] | None = None

    @property
    def passed(self) -> bool:
        return all(outcome.passed for outcome in self.outcomes)

    @property
    def refused_at(self) -> GateOutcome | None:
        return next((outcome for outcome in self.outcomes if not outcome.passed), None)

    @property
    def differs_from(self) -> list[uuid.UUID]:
        found = self._outcome(DUPLICATE_GATE)
        return list(found.related) if found is not None and found.passed else []

    @property
    def held_instead(self) -> list[uuid.UUID]:
        refused = self.refused_at
        if refused is None or refused.gate not in (DUPLICATE_GATE, NOVELTY_GATE):
            return []
        return list(refused.related)

    def _outcome(self, gate: str) -> GateOutcome | None:
        return next((outcome for outcome in self.outcomes if outcome.gate == gate), None)


@dataclass(frozen=True)
class _Held:
    twin: HeldFact | None
    nearest: tuple[HeldFact, ...]
    close: tuple[HeldFact, ...]


def first_gates(candidate: Candidate, sources: Sequence[CitedSource]) -> tuple[GateOutcome, ...]:
    quoted = quote_gate(candidate.statement, sources)
    if not quoted.passed:
        return (quoted,)
    return quoted, source_gate(candidate.statement, candidate.field, sources)


def gate_run(candidate: Candidate, first: Sequence[GateOutcome], later: LaterGates | None) -> GateRun:
    if later is None:
        return GateRun(candidate, tuple(first))
    return GateRun(candidate, (*first, *later.outcomes), later.vector)


async def later_gates(
    store: HeldFacts,
    candidates: Sequence[Candidate],
    *,
    embed: TextEmbedder | None,
    judge: StructuredModel | None,
) -> dict[str, LaterGates]:
    if not candidates:
        return {}
    vectors = await _vectors(embed, candidates)
    held = {
        candidate.ref: await _held(store, candidate, vectors.get(candidate.ref)) for candidate in candidates
    }
    duplicates = await _duplicates(judge, candidates, held, vectored=embed is not None)
    passing = [candidate for candidate in candidates if duplicates[candidate.ref].passed]
    novelty = await _novelty(judge, passing, held, duplicates) if embed is not None else {}
    return {
        candidate.ref: LaterGates(
            outcomes=tuple(
                o for o in (duplicates[candidate.ref], novelty.get(candidate.ref)) if o is not None
            ),
            vector=vectors.get(candidate.ref),
        )
        for candidate in candidates
    }


async def _vectors(embed: TextEmbedder | None, candidates: Sequence[Candidate]) -> dict[str, list[float]]:
    if embed is None:
        return {}
    texts = [document_text(candidate.statement) for candidate in candidates]
    found = checked_vectors(await embed(texts), expected=len(texts))
    return {candidate.ref: vector for candidate, vector in zip(candidates, found, strict=True)}


async def _held(store: HeldFacts, candidate: Candidate, vector: list[float] | None) -> _Held:
    nearest = tuple(await store.nearest(candidate.field, vector, NOVELTY_FACTS_MAX)) if vector else ()
    twins = await store.twins(candidate.field, candidate.statement)
    twin = held_twin(candidate.statement, [*twins, *nearest])
    return _Held(twin=twin, nearest=nearest, close=tuple(close_facts(nearest)))


async def _duplicates(
    judge: StructuredModel | None,
    candidates: Sequence[Candidate],
    held: Mapping[str, _Held],
    *,
    vectored: bool,
) -> dict[str, GateOutcome]:
    asks = [
        JudgeAsk(c, held[c.ref].close) for c in candidates if held[c.ref].twin is None and held[c.ref].close
    ]
    compared: dict[str, list[FactComparison]] = {}
    model = None
    if asks and judge is not None:
        reply, model = await _judged(judge, comparison_request(asks))
        compared = parsed_comparisons(reply, asks)
    return {
        candidate.ref: duplicate_outcome(
            candidate,
            twin=held[candidate.ref].twin,
            close=held[candidate.ref].close,
            comparisons=compared.get(candidate.ref),
            model=model,
            vectored=vectored,
        )
        for candidate in candidates
    }


async def _novelty(
    judge: StructuredModel | None,
    candidates: Sequence[Candidate],
    held: Mapping[str, _Held],
    duplicates: Mapping[str, GateOutcome],
) -> dict[str, GateOutcome]:
    asks = [
        JudgeAsk(candidate, held[candidate.ref].nearest)
        for candidate in candidates
        if held[candidate.ref].nearest and not duplicates[candidate.ref].related
    ]
    verdicts: dict[str, NoveltyVerdict] = {}
    model = None
    if asks and judge is not None:
        reply, model = await _judged(judge, novelty_request(asks))
        verdicts = parsed_novelty(reply, asks)
    found: dict[str, GateOutcome] = {}
    for candidate in candidates:
        outcome = novelty_outcome(
            candidate,
            differs=duplicates[candidate.ref].related,
            held_count=len(held[candidate.ref].nearest),
            verdict=verdicts.get(candidate.ref),
            model=model,
        )
        if outcome is not None:
            found[candidate.ref] = outcome
    return found


async def _judged(judge: StructuredModel, request: JudgeRequest) -> tuple[dict[str, object], str | None]:
    reply = await judge(system=request.system, user=request.user, schema=request.schema)
    return reply_object(reply), reply.model
