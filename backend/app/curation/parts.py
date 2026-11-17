from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Self

from pydantic import AfterValidator, Field, model_validator

from app.models.knowledge import QUOTE_MAX_CHARS
from app.research.base import ContractModel, HttpsUrl
from app.research.evidence import DOI_PATTERN
from app.research.vocabulary import Discipline, TrustTier

from .fields import (
    ID_PATTERNS,
    SUBJECT_KINDS,
    ClaimId,
    ClaimIds,
    NameList,
    NameText,
    QuestionId,
    SentenceText,
    SourceId,
    distinct,
)
from .limits import YEAR_MAX, YEAR_MIN
from .vocabulary import CuratedSourceKind, Sensitivity, SourceAccess, SourceSubKind, SubjectType

__all__ = [
    "LANGUAGE_PATTERN",
    "WAYBACK_SNAPSHOT_PATTERN",
    "CitedQuote",
    "Claim",
    "Conflict",
    "OpenQuestion",
    "Search",
    "Source",
    "Subject",
]

WAYBACK_SNAPSHOT_PATTERN = r"^https://web\.archive\.org/web/\d{4,14}(?:[a-z]{2}_)?/https?://\S+$"
LANGUAGE_PATTERN = r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$"


class Search(ContractModel):
    query: str = Field(min_length=1, max_length=300)
    site: str = Field(min_length=1, max_length=200)


class Source(ContractModel):
    id: SourceId
    kind: CuratedSourceKind
    sub_kind: SourceSubKind | None = None
    title: str = Field(min_length=1, max_length=1000)
    authors: NameList = Field(default_factory=list)
    publisher: str | None = Field(default=None, min_length=1, max_length=300)
    year: int | None = Field(default=None, ge=YEAR_MIN, le=YEAR_MAX)
    url: HttpsUrl
    doi: str | None = Field(default=None, pattern=DOI_PATTERN)
    archived_url: Annotated[HttpsUrl, Field(pattern=WAYBACK_SNAPSHOT_PATTERN)] | None = None
    language: str = Field(pattern=LANGUAGE_PATTERN)
    licence: str | None = Field(default=None, min_length=1, max_length=200)
    access: SourceAccess
    reliability: TrustTier
    retrieved_at: date

    @model_validator(mode="after")
    def _sub_kind_only_for_other(self) -> Self:
        if self.sub_kind is not None and self.kind != "OTHER":
            raise ValueError(f"source {self.id} gives subKind only with kind OTHER")
        return self


class CitedQuote(ContractModel):
    source_id: SourceId
    locator: str = Field(min_length=1, max_length=200)
    quote: str = Field(min_length=1, max_length=QUOTE_MAX_CHARS)


class Subject(ContractModel):
    type: SubjectType
    ref: str | None = None

    @model_validator(mode="after")
    def _ref_matches_type(self) -> Self:
        kind = SUBJECT_KINDS.get(self.type)
        if kind is None and self.ref is not None:
            raise ValueError("a CRAFT subject has no ref")
        if kind is not None and (self.ref is None or not re.fullmatch(ID_PATTERNS[kind], self.ref)):
            raise ValueError(f"a {self.type} subject's ref is a {kind} id ({ID_PATTERNS[kind]})")
        return self


class Claim(ContractModel):
    id: ClaimId
    discipline: Discipline
    subject: Subject
    text: SentenceText
    quotes: list[CitedQuote] = Field(min_length=1)
    hypothesis: bool = False
    sensitivity: Sensitivity = "OPEN"


class Conflict(ContractModel):
    claim_ids: Annotated[list[ClaimId], Field(min_length=2), AfterValidator(distinct)]
    about: NameText


class OpenQuestion(ContractModel):
    id: QuestionId
    question: SentenceText
    claim_ids: ClaimIds
    settled_by: SentenceText | None = None
