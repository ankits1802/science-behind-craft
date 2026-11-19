from __future__ import annotations

import uuid
from collections.abc import Callable, Collection, Hashable, Mapping, Sequence
from dataclasses import dataclass
from statistics import fmean
from typing import Any

from pydantic import Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import Claim
from app.research.base import ContractModel
from app.research.crafts import QUESTION_MAX_CHARS
from app.research.retrieval import (
    HIDDEN_CLAIM_STATUSES,
    VISIBLE_SENSITIVITY,
    KnowledgeQuery,
    KnowledgeRetriever,
)
from app.research.vocabulary import Discipline

__all__ = [
    "EVAL_DEPTH",
    "EVAL_MODE",
    "RECALL_DEPTH",
    "GoldenQuestion",
    "QuestionResult",
    "RetrievalReport",
    "evaluate_golden",
    "recall_at",
    "reciprocal_rank",
    "visible_claims",
]

RECALL_DEPTH = 5
EVAL_DEPTH = 10
EVAL_MODE = "HYBRID"
DIGITS = 4


class GoldenQuestion(ContractModel):
    key: str = Field(min_length=1, max_length=80)
    craft_slug: str | None = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    expected: tuple[str, ...] = Field(min_length=1)
    fields: tuple[Discipline, ...] = ()

    @field_validator("expected")
    @classmethod
    def _distinct(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(values)) != len(values):
            raise ValueError("Each expected hit may appear once")
        return values


@dataclass(frozen=True)
class QuestionResult:
    key: str
    recall: float
    reciprocal_rank: float
    missed: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalReport:
    results: tuple[QuestionResult, ...]
    absent: tuple[str, ...] = ()

    @property
    def recall_at_depth(self) -> float | None:
        return fmean(result.recall for result in self.results) if self.results else None

    @property
    def mean_reciprocal_rank(self) -> float | None:
        return fmean(result.reciprocal_rank for result in self.results) if self.results else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "questions": len(self.results),
            f"recallAt{RECALL_DEPTH}": _rounded(self.recall_at_depth),
            "meanReciprocalRank": _rounded(self.mean_reciprocal_rank),
            "absent": list(self.absent),
            "misses": {result.key: list(result.missed) for result in self.results if result.missed},
        }


def recall_at[K: Hashable](ranked: Sequence[K], expected: Collection[K], depth: int) -> float:
    wanted = set(expected)
    if not wanted:
        raise InvalidInput("Recall needs at least one expected hit")
    return len(set(ranked[:depth]) & wanted) / len(wanted)


def reciprocal_rank[K: Hashable](ranked: Sequence[K], expected: Collection[K]) -> float:
    wanted = set(expected)
    if not wanted:
        raise InvalidInput("A reciprocal rank needs at least one expected hit")
    return next((1.0 / rank for rank, key in enumerate(ranked, start=1) if key in wanted), 0.0)


async def evaluate_golden(
    retriever: KnowledgeRetriever,
    golden: Sequence[GoldenQuestion],
    *,
    claim_id: Callable[[str], uuid.UUID],
    present: Collection[uuid.UUID] | None = None,
) -> RetrievalReport:
    results: list[QuestionResult] = []
    absent: list[str] = []
    for question in golden:
        expected = {claim_id(key): key for key in question.expected}
        if present is not None:
            absent += [key for found, key in expected.items() if found not in present]
            expected = {found: key for found, key in expected.items() if found in present}
        if expected:
            results.append(await _asked(retriever, question, expected))
    return RetrievalReport(tuple(results), tuple(absent))


async def visible_claims(session: AsyncSession, claim_ids: Collection[uuid.UUID]) -> set[uuid.UUID]:
    found = await session.scalars(
        select(Claim.id).where(
            Claim.id.in_(list(claim_ids)),
            Claim.status.not_in(HIDDEN_CLAIM_STATUSES),
            Claim.sensitivity == VISIBLE_SENSITIVITY,
        )
    )
    return set(found)


async def _asked(
    retriever: KnowledgeRetriever, question: GoldenQuestion, expected: Mapping[uuid.UUID, str]
) -> QuestionResult:
    query = KnowledgeQuery(
        craft_slug=question.craft_slug,
        text=question.question,
        mode=EVAL_MODE,
        fields=question.fields,
        limit=EVAL_DEPTH,
    )
    ranked = [hit.claim_id for hit in (await retriever.search(query)).claims]
    return QuestionResult(
        key=question.key,
        recall=recall_at(ranked, expected, RECALL_DEPTH),
        reciprocal_rank=reciprocal_rank(ranked, expected),
        missed=tuple(key for found, key in expected.items() if found not in ranked[:RECALL_DEPTH]),
    )


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, DIGITS)
