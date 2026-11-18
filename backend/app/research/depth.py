from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Self

from pydantic import Field, model_validator

from app.core.errors import InvalidInput
from app.core.roles import (
    ADMIN,
    ARTISAN,
    MASTER_ADMIN,
    PROFESSOR,
    RESEARCHER,
    ROLE_RANK,
    STUDENT,
    is_uncapped,
    role_value,
)
from app.models.enums import DISCIPLINES, EXPLAINER_DEPTHS

from .base import ContractModel
from .planning import MODE_POLICIES
from .vocabulary import AnswerMode, Depth

__all__ = [
    "DEGRADED_DEPTHS",
    "DEPTH_LABELS",
    "DEPTH_ORDER",
    "DEPTH_POLICIES",
    "LEAST_DEPTH",
    "ROLE_DEFAULT_DEPTHS",
    "DepthPolicy",
    "ResearchBudget",
    "default_depth",
    "depth_at_least",
    "depth_policy",
    "effective_depth",
    "research_budget",
    "section_sentence_limit",
    "selectable_depths",
]

DEPTH_LABELS: Mapping[str, str] = MappingProxyType(
    {"BASIC": "Basic", "DETAILED": "Detailed", "EXPERT": "Expert"}
)
DEPTH_ORDER: Mapping[str, int] = MappingProxyType(
    {depth: rank for rank, depth in enumerate(EXPLAINER_DEPTHS)}
)
LEAST_DEPTH = EXPLAINER_DEPTHS[0]


class DepthPolicy(ContractModel):
    depth: Depth
    label: str = Field(min_length=1)
    mode: AnswerMode
    min_sections: int = Field(ge=1)
    max_sections: int = Field(ge=1)
    min_experts: int = Field(ge=1)
    max_experts: int = Field(ge=1)
    max_queries: int = Field(ge=0)
    max_fetches: int = Field(ge=0)
    section_sentences: int = Field(ge=1)
    stored_claims: int = Field(ge=1)

    @model_validator(mode="after")
    def _ranges_in_order(self) -> Self:
        if self.min_sections > self.max_sections or self.min_experts > self.max_experts:
            raise ValueError(f"{self.depth} ranges run from their minimum to their maximum")
        if self.label != DEPTH_LABELS[self.depth]:
            raise ValueError(f"{self.depth} is shown as {DEPTH_LABELS[self.depth]!r}")
        mode = MODE_POLICIES[self.mode]
        if self.max_queries > mode.max_queries or self.max_fetches > mode.max_fetches:
            raise ValueError(f"{self.depth} researches within the limits of {self.mode}")
        return self


class ResearchBudget(ContractModel):
    max_queries: int = Field(ge=0)
    max_fetches: int = Field(ge=0)


DEPTH_POLICIES: Mapping[str, DepthPolicy] = MappingProxyType(
    {
        "BASIC": DepthPolicy(
            depth="BASIC",
            label="Basic",
            mode="HYBRID",
            min_sections=3,
            max_sections=4,
            min_experts=2,
            max_experts=2,
            max_queries=2,
            max_fetches=5,
            section_sentences=8,
            stored_claims=20,
        ),
        "DETAILED": DepthPolicy(
            depth="DETAILED",
            label="Detailed",
            mode="HYBRID",
            min_sections=5,
            max_sections=7,
            min_experts=4,
            max_experts=4,
            max_queries=4,
            max_fetches=10,
            section_sentences=8,
            stored_claims=20,
        ),
        "EXPERT": DepthPolicy(
            depth="EXPERT",
            label="Expert",
            mode="DEEP",
            min_sections=1,
            max_sections=len(DISCIPLINES),
            min_experts=6,
            max_experts=12,
            max_queries=24,
            max_fetches=48,
            section_sentences=16,
            stored_claims=40,
        ),
    }
)
ROLE_DEFAULT_DEPTHS: Mapping[str, str] = MappingProxyType(
    {
        STUDENT: "BASIC",
        ARTISAN: "BASIC",
        RESEARCHER: "DETAILED",
        PROFESSOR: "DETAILED",
        ADMIN: "EXPERT",
        MASTER_ADMIN: "EXPERT",
    }
)
DEGRADED_DEPTHS: Mapping[str, str] = MappingProxyType({"EXPERT": "DETAILED"})


def depth_policy(depth: str) -> DepthPolicy:
    policy = DEPTH_POLICIES.get(depth)
    if policy is None:
        raise InvalidInput(f"Unknown depth {depth!r}")
    return policy


def default_depth(user_or_role: object) -> str:
    return ROLE_DEFAULT_DEPTHS.get(role_value(user_or_role), LEAST_DEPTH)


def selectable_depths(user_or_role: object) -> tuple[str, ...]:
    return EXPLAINER_DEPTHS if role_value(user_or_role) in ROLE_RANK else ()


def depth_at_least(have: str, want: str) -> bool:
    return DEPTH_ORDER[depth_policy(have).depth] >= DEPTH_ORDER[depth_policy(want).depth]


def effective_depth(depth: str, user_or_role: object, *, past_degrade: bool) -> str:
    depth_policy(depth)
    if not past_degrade or is_uncapped(user_or_role):
        return depth
    return DEGRADED_DEPTHS.get(depth, depth)


def research_budget(mode: str, depth: str | None = None) -> ResearchBudget:
    limits = MODE_POLICIES[mode]
    if depth is None:
        return ResearchBudget(max_queries=limits.max_queries, max_fetches=limits.max_fetches)
    chosen = depth_policy(depth)
    return ResearchBudget(
        max_queries=min(limits.max_queries, chosen.max_queries),
        max_fetches=min(limits.max_fetches, chosen.max_fetches),
    )


def section_sentence_limit(depth: str | None) -> int:
    return depth_policy(depth or LEAST_DEPTH).section_sentences
