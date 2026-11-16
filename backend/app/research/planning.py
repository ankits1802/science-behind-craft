from __future__ import annotations

import uuid
from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal, Protocol, Self, runtime_checkable

from pydantic import Field, field_validator, model_validator

from .base import ContractModel
from .crafts import QUESTION_MAX_CHARS, CraftRef
from .evidence import SearchQuery
from .retrieval import MODE_CLAIM_LEVELS
from .vocabulary import RETRIEVAL_TIERS, AnswerLanguage, AnswerMode, FacetType, LiveTier, RetrievalTier

__all__ = [
    "COVERING_LEVELS",
    "FACET_COVERED_MIN_CLAIMS",
    "MAX_FACETS",
    "MODE_POLICIES",
    "PLAN_INTENTS",
    "WITHHELD_TERMS_MAX",
    "Facet",
    "FacetCoverage",
    "ModePolicy",
    "PlanRequest",
    "PlannedQuery",
    "Planner",
    "RetrievalPlan",
]

PLAN_SCHEMA_VERSION = 1
MAX_FACETS = 8
PLAN_INTENTS = ("OVERVIEW", "MATERIALS", "PROCESS", "SCIENCE", "PLACE", "HISTORY", "COMPARISON", "OTHER")

WITHHELD_TERMS_MAX = 20
FACET_COVERED_MIN_CLAIMS = 2
OPEN_QUESTION_LEVEL = "HYPOTHESIS"

PlanIntent = Literal[*PLAN_INTENTS]


class ModePolicy(ContractModel):
    mode: AnswerMode
    tiers: tuple[RetrievalTier, ...]
    live_only_for_open_facets: bool
    max_queries: int = Field(ge=0)
    max_fetches: int = Field(ge=0)


MODE_POLICIES: Mapping[str, ModePolicy] = MappingProxyType(
    {
        "VERIFIED": ModePolicy(
            mode="VERIFIED", tiers=("T0", "T1"), live_only_for_open_facets=True, max_queries=0, max_fetches=0
        ),
        "HYBRID": ModePolicy(
            mode="HYBRID",
            tiers=RETRIEVAL_TIERS,
            live_only_for_open_facets=True,
            max_queries=4,
            max_fetches=10,
        ),
        "DEEP": ModePolicy(
            mode="DEEP", tiers=RETRIEVAL_TIERS, live_only_for_open_facets=False, max_queries=8, max_fetches=20
        ),
    }
)


COVERING_LEVELS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        mode: tuple(level for level in levels if level != OPEN_QUESTION_LEVEL)
        for mode, levels in MODE_CLAIM_LEVELS.items()
    }
)


class Facet(ContractModel):
    type: FacetType
    target: str = Field(min_length=1, max_length=200)


class PlannedQuery(ContractModel):
    tier: LiveTier
    facet_index: int = Field(ge=0)
    query: SearchQuery


class PlanRequest(ContractModel):
    question: str = Field(min_length=2, max_length=QUESTION_MAX_CHARS)
    mode: AnswerMode
    craft: CraftRef
    language: AnswerLanguage = "en"
    withheld_terms: tuple[str, ...] = Field(default=(), max_length=WITHHELD_TERMS_MAX)

    @field_validator("withheld_terms")
    @classmethod
    def _terms_are_words(cls, terms: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(term.strip() for term in terms)
        if any(len(term) < 2 or len(term) > 200 for term in cleaned):
            raise ValueError("a withheld term is 2 to 200 characters")
        return cleaned


class FacetCoverage(ContractModel):
    facet_index: int = Field(ge=0)
    claim_ids: tuple[uuid.UUID, ...] = ()

    @property
    def covered(self) -> bool:
        return len(self.claim_ids) >= FACET_COVERED_MIN_CLAIMS


class RetrievalPlan(ContractModel):
    schema_version: Literal[1] = PLAN_SCHEMA_VERSION
    mode: AnswerMode
    craft: CraftRef
    intent: PlanIntent
    language: AnswerLanguage
    needs_region: bool
    facets: list[Facet] = Field(min_length=1, max_length=MAX_FACETS)
    tiers: list[RetrievalTier] = Field(min_length=1)
    queries: list[PlannedQuery] = Field(default_factory=list)
    max_fetches: int = Field(ge=0)

    @model_validator(mode="after")
    def _within_the_mode(self) -> Self:
        policy = MODE_POLICIES[self.mode]
        if any(tier not in policy.tiers for tier in self.tiers):
            raise ValueError(f"{self.mode} runs only tiers {', '.join(policy.tiers)}")
        if self.tiers != sorted(set(self.tiers), key=RETRIEVAL_TIERS.index):
            raise ValueError("tiers are listed once each, in tier order")
        if len(self.queries) > policy.max_queries:
            raise ValueError(f"{self.mode} sends at most {policy.max_queries} queries")
        if self.max_fetches > policy.max_fetches:
            raise ValueError(f"{self.mode} fetches at most {policy.max_fetches} documents")
        for query in self.queries:
            if query.tier not in self.tiers:
                raise ValueError(f"a {query.tier} query needs {query.tier} in tiers")
            if query.facet_index >= len(self.facets):
                raise ValueError("a query names a facet by its index in facets")
        return self


@runtime_checkable
class Planner(Protocol):
    async def plan(self, request: PlanRequest) -> RetrievalPlan: ...
