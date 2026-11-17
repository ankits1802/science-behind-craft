from __future__ import annotations

from typing import Annotated, Literal, Protocol, Self, runtime_checkable

from pydantic import Field, model_validator

from .base import ContractModel
from .untrusted import untrusted_block

__all__ = [
    "ACCEPT_MARGIN",
    "ACCEPT_SCORE",
    "ANY_CRAFT_LINE",
    "COMPARED_CRAFTS_MAX",
    "CRAFT_NAME_MAX_CHARS",
    "FUZZY_MIN_SIMILARITY",
    "MATCH_REASON_KINDS",
    "MAX_CANDIDATES",
    "QUESTION_MAX_CHARS",
    "RESOLUTION_STATUSES",
    "SLUG_MAX_CHARS",
    "CraftCandidate",
    "CraftQuery",
    "CraftRef",
    "CraftResolution",
    "CraftResolver",
    "MatchReason",
    "clear_winner",
    "craft_block",
    "craft_line",
]

ACCEPT_SCORE = 0.85
ACCEPT_MARGIN = 0.15
FUZZY_MIN_SIMILARITY = 0.85
MAX_CANDIDATES = 5
COMPARED_CRAFTS_MAX = 3
QUESTION_MAX_CHARS = 1000
CRAFT_NAME_MAX_CHARS = 300
SLUG_MAX_CHARS = 200
MATCH_REASON_KINDS = (
    "EXACT_SLUG",
    "EXACT_NAME",
    "EXACT_ALIAS",
    "EXACT_SPELLING",
    "MERGED_REDIRECT",
    "FUZZY",
    "SEMANTIC",
    "PLACE",
    "FAMILY",
    "MODEL_CHOICE",
)
RESOLUTION_STATUSES = ("RESOLVED", "AMBIGUOUS", "NONE")
ANY_CRAFT_LINE = "Craft: any craft (the question names none on the list)"

MatchReasonKind = Literal[*MATCH_REASON_KINDS]
ResolutionStatus = Literal[*RESOLUTION_STATUSES]
Score = Annotated[float, Field(ge=0.0, le=1.0)]


class CraftRef(ContractModel):
    slug: str = Field(min_length=1, max_length=SLUG_MAX_CHARS)
    name: str = Field(min_length=1, max_length=CRAFT_NAME_MAX_CHARS)
    path: str

    @model_validator(mode="after")
    def _path_names_the_slug(self) -> Self:
        if self.path != f"/crafts/{self.slug}":
            raise ValueError("path is /crafts/<slug>")
        return self


class CraftQuery(ContractModel):
    text: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    craft_slug: str | None = Field(default=None, max_length=SLUG_MAX_CHARS)
    language: str | None = Field(default=None, max_length=16)


class MatchReason(ContractModel):
    kind: MatchReasonKind
    matched: str = Field(min_length=1, max_length=300)
    score: Score


class CraftCandidate(ContractModel):
    craft: CraftRef
    score: Score
    reasons: list[MatchReason] = Field(min_length=1)


class CraftResolution(ContractModel):
    status: ResolutionStatus
    craft: CraftRef | None
    candidates: list[CraftCandidate] = Field(max_length=MAX_CANDIDATES)
    normalised: str
    script: str = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def _status_matches_candidates(self) -> Self:
        scores = [c.score for c in self.candidates]
        if scores != sorted(scores, reverse=True):
            raise ValueError("candidates are ranked by score, highest first")
        if self.status == "RESOLVED":
            if self.craft is None or not self.candidates or self.candidates[0].craft != self.craft:
                raise ValueError("a resolved craft is the top candidate")
        elif self.craft is not None:
            raise ValueError(f"{self.status} names no craft")
        if self.status == "AMBIGUOUS" and not self.candidates:
            raise ValueError("an ambiguous resolution offers at least one candidate")
        if self.status == "NONE" and self.candidates:
            raise ValueError("NONE offers no candidates")
        return self


def clear_winner(candidates: list[CraftCandidate]) -> bool:
    if not candidates:
        return False
    top = candidates[0].score
    runner_up = candidates[1].score if len(candidates) > 1 else 0.0
    return top >= ACCEPT_SCORE and round(top - runner_up, 9) >= ACCEPT_MARGIN


@runtime_checkable
class CraftResolver(Protocol):
    async def resolve(self, query: CraftQuery) -> CraftResolution: ...


def craft_block(craft: CraftRef) -> str:
    return untrusted_block("craft", "craft name and slug", f"{craft.name} (slug {craft.slug})")


def craft_line(craft: CraftRef | None) -> str:
    return craft_block(craft) if craft else ANY_CRAFT_LINE
