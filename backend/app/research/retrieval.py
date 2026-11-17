from __future__ import annotations

import uuid
from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal, Protocol, runtime_checkable

from pydantic import Field, field_validator

from app.models.enums import CLAIM_STATUSES, EVIDENCE_LEVELS

from .base import ContractModel
from .crafts import QUESTION_MAX_CHARS
from .vocabulary import AnswerMode, ChunkAcl, EvidenceLevel, FacetType

__all__ = [
    "CLAIM_SUBJECT_TYPES",
    "HIDDEN_CLAIM_STATUSES",
    "KNOWLEDGE_RESULT_MAX",
    "MODE_CLAIM_LEVELS",
    "MODE_CLAIM_STATUSES",
    "RESTRICTED_SENSITIVITY",
    "VISIBLE_SENSITIVITY",
    "ChunkHit",
    "ClaimHit",
    "KnowledgeHits",
    "KnowledgeQuery",
    "KnowledgeRetriever",
]

KNOWLEDGE_RESULT_MAX = 50
KNOWLEDGE_RESULT_DEFAULT = 12
CLAIM_SUBJECT_TYPES = ("CONCEPT", "EDGE")
HIDDEN_CLAIM_STATUSES = ("DRAFT", "REJECTED", "RETRACTED")
VISIBLE_SENSITIVITY = "OPEN"
RESTRICTED_SENSITIVITY = "RESTRICTED"
VERIFIED_MODE_LEVELS = ("VERIFIED", "REVIEWED")
SHOWN_CLAIM_STATUSES = tuple(status for status in CLAIM_STATUSES if status not in HIDDEN_CLAIM_STATUSES)

MODE_CLAIM_LEVELS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {"VERIFIED": VERIFIED_MODE_LEVELS, "HYBRID": EVIDENCE_LEVELS, "DEEP": EVIDENCE_LEVELS}
)
MODE_CLAIM_STATUSES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {"VERIFIED": ("APPROVED",), "HYBRID": SHOWN_CLAIM_STATUSES, "DEEP": SHOWN_CLAIM_STATUSES}
)

ClaimSubjectType = Literal[*CLAIM_SUBJECT_TYPES]


class KnowledgeQuery(ContractModel):
    craft_slug: str | None = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    mode: AnswerMode
    facets: tuple[FacetType, ...] = ()
    chunk_acls: tuple[ChunkAcl, ...] = ("PUBLIC",)
    limit: int = Field(default=KNOWLEDGE_RESULT_DEFAULT, ge=1, le=KNOWLEDGE_RESULT_MAX)

    @field_validator("facets", "chunk_acls")
    @classmethod
    def _distinct(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(values)) != len(values):
            raise ValueError("Each value may appear once")
        return values


class ClaimHit(ContractModel):
    claim_id: uuid.UUID
    text: str = Field(min_length=1)
    level: EvidenceLevel
    subject_type: ClaimSubjectType
    subject_id: uuid.UUID
    score: float = Field(gt=0)
    lexical_rank: int | None = Field(default=None, ge=1)
    vector_rank: int | None = Field(default=None, ge=1)


class ChunkHit(ContractModel):
    chunk_id: uuid.UUID
    source_id: uuid.UUID
    ordinal: int = Field(ge=0)
    locator: str | None = None
    text: str = Field(min_length=1)
    score: float = Field(gt=0)
    lexical_rank: int | None = Field(default=None, ge=1)
    vector_rank: int | None = Field(default=None, ge=1)


class KnowledgeHits(ContractModel):
    craft_slug: str | None
    claims: tuple[ClaimHit, ...] = ()
    chunks: tuple[ChunkHit, ...] = ()


@runtime_checkable
class KnowledgeRetriever(Protocol):
    async def search(self, query: KnowledgeQuery) -> KnowledgeHits: ...
