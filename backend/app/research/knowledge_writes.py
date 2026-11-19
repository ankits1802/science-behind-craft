from __future__ import annotations

import uuid
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from app.models.knowledge import QUOTE_MAX_CHARS

from .base import ContractModel, HttpsUrl
from .candidate_gates import Gate, GateOutcome
from .evidence import canonical_url, personal_data_in
from .review_switch import ProposalOutcome
from .vocabulary import Discipline, EvidenceLevel

__all__ = [
    "KNOWLEDGE_WRITES_SCHEMA_VERSION",
    "PROPOSAL_FIELDS_MAX",
    "PROPOSAL_QUOTES_MAX",
    "PROPOSAL_SOURCES_MAX",
    "PROPOSAL_SUBJECT_KINDS",
    "STATEMENT_MAX_CHARS",
    "FactProposal",
    "GateReport",
    "ProposalReply",
    "ProposalSubject",
    "ProposedQuote",
    "ProposedSource",
    "gate_reports",
]

KNOWLEDGE_WRITES_SCHEMA_VERSION = 1
PROPOSAL_SUBJECT_KINDS = ("craft", "category")
PROPOSAL_SOURCES_MAX = 5
PROPOSAL_QUOTES_MAX = 6
PROPOSAL_FIELDS_MAX = 3
STATEMENT_MIN_CHARS = 20
STATEMENT_MAX_CHARS = 1000
SUBJECT_SLUG_MAX_CHARS = 200
TITLE_MAX_CHARS = 1000
LICENCE_MAX_CHARS = 200
LOCATOR_MAX_CHARS = 300

SubjectKind = Literal[*PROPOSAL_SUBJECT_KINDS]


class ProposalSubject(ContractModel):
    kind: SubjectKind
    slug: str = Field(min_length=1, max_length=SUBJECT_SLUG_MAX_CHARS, pattern=r"^[A-Za-z0-9-]+$")


class ProposedQuote(ContractModel):
    text: str = Field(min_length=1, max_length=QUOTE_MAX_CHARS)
    locator: str | None = Field(default=None, min_length=1, max_length=LOCATOR_MAX_CHARS)


class ProposedSource(ContractModel):
    url: HttpsUrl
    title: str = Field(min_length=1, max_length=TITLE_MAX_CHARS)
    licence: str | None = Field(default=None, min_length=1, max_length=LICENCE_MAX_CHARS)
    quotes: list[ProposedQuote] = Field(min_length=1, max_length=PROPOSAL_QUOTES_MAX)

    @model_validator(mode="after")
    def _each_quote_once(self) -> Self:
        texts = [quote.text for quote in self.quotes]
        if len(set(texts)) != len(texts):
            raise ValueError("a source gives each quote once")
        return self


class FactProposal(ContractModel):
    schema_version: Literal[1] = KNOWLEDGE_WRITES_SCHEMA_VERSION
    subject: ProposalSubject
    field: Discipline
    fields: list[Discipline] = Field(default_factory=list, max_length=PROPOSAL_FIELDS_MAX)
    statement: str = Field(min_length=STATEMENT_MIN_CHARS, max_length=STATEMENT_MAX_CHARS)
    sources: list[ProposedSource] = Field(min_length=1, max_length=PROPOSAL_SOURCES_MAX)

    @field_validator("statement")
    @classmethod
    def _no_personal_data(cls, value: str) -> str:
        found = personal_data_in(value)
        if found:
            raise ValueError(f"a fact never carries personal data ({', '.join(found)})")
        return value

    @model_validator(mode="after")
    def _fields_and_sources_are_distinct(self) -> Self:
        if self.field in self.fields or len(set(self.fields)) != len(self.fields):
            raise ValueError("secondary fields are distinct and leave out the primary field")
        urls = [canonical_url(source.url) for source in self.sources]
        if len(set(urls)) != len(urls):
            raise ValueError("each source is named once; give all its quotes under it")
        return self


class GateReport(ContractModel):
    gate: Gate
    passed: bool
    reasons: list[str]


class ProposalReply(ContractModel):
    schema_version: Literal[1] = KNOWLEDGE_WRITES_SCHEMA_VERSION
    outcome: ProposalOutcome
    claim_id: uuid.UUID
    status: str
    level: EvidenceLevel
    approved_at_once: bool
    in_review_queue: bool
    sources_differ: bool
    differs_from: list[uuid.UUID]
    gates: list[GateReport]
    message: str


def gate_reports(outcomes: list[GateOutcome]) -> list[GateReport]:
    return [GateReport(gate=item.gate, passed=item.passed, reasons=list(item.reasons)) for item in outcomes]
