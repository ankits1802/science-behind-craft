from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Literal, Protocol, Self, runtime_checkable

from pydantic import Field, field_validator, model_validator

from app.core.errors import InvalidInput
from app.models.knowledge import QUOTE_MAX_CHARS

from .base import ContractModel
from .crafts import QUESTION_MAX_CHARS, CraftRef
from .evidence import EVIDENCE_ID_MAX_CHARS, SEARCH_QUERY_MAX_CHARS
from .quotes import (
    QUOTE_MIN_CHARS,
    QUOTE_OVERLAP_MIN,
    quote_occurs,
    quote_overlap,
    trivial_quote,
    unsupported_figures,
)
from .vocabulary import (
    CANONICAL_LANGUAGE,
    AnswerLanguage,
    AnswerMode,
    Discipline,
    EvidenceLevel,
    LiveTier,
    weakest_level,
)

__all__ = [
    "CANDIDATE_KINDS",
    "COMPOSE_RETRIES",
    "FOLLOW_UPS_MAX",
    "HEADING_MAX_CHARS",
    "SENTENCE_MAX_CHARS",
    "VIOLATION_KINDS",
    "ComposeCandidate",
    "ComposeFocus",
    "ComposeRequest",
    "ComposedAnswer",
    "ComposedSection",
    "ComposedSentence",
    "Composer",
    "QuotedSpan",
    "ResearchSummary",
    "SearchedQuery",
    "SentenceViolation",
    "StageOption",
    "not_enough_evidence_message",
    "searched_note",
    "sentence_level",
    "sentence_violations",
]

COMPOSE_RETRIES = 1
SENTENCE_MAX_CHARS = 600
HEADING_MAX_CHARS = 120
FOLLOW_UPS_MAX = 5
CANDIDATE_KINDS = ("CLAIM", "EVIDENCE")
VIOLATION_KINDS = (
    "UNCITED",
    "UNKNOWN_ID",
    "UNQUOTED",
    "UNSUPPORTED_FIGURE",
    "SPAN_NOT_CITED",
    "SPAN_NOT_IN_SOURCE",
    "TRIVIAL_QUOTE",
    "UNRELATED_QUOTE",
)

CandidateKind = Literal[*CANDIDATE_KINDS]
ViolationKind = Literal[*VIOLATION_KINDS]


class ComposeCandidate(ContractModel):
    id: str = Field(min_length=3, max_length=EVIDENCE_ID_MAX_CHARS)
    kind: CandidateKind
    text: str = Field(min_length=1)
    quotes: list[str] = Field(default_factory=list)
    source_label: str = Field(min_length=1, max_length=300)
    level: EvidenceLevel

    @model_validator(mode="after")
    def _id_fits_the_kind(self) -> Self:
        if self.kind == "CLAIM":
            uuid.UUID(self.id)
        elif ":" not in self.id:
            raise ValueError("an EVIDENCE candidate has an '<adapter>:<id>' id")
        return self

    @property
    def cited_texts(self) -> list[str]:
        return [self.text, *self.quotes]


class SearchedQuery(ContractModel):
    tier: LiveTier
    text: str = Field(min_length=2, max_length=SEARCH_QUERY_MAX_CHARS)


class ResearchSummary(ContractModel):
    craft: CraftRef | None
    mode: AnswerMode
    stored_claims: int = Field(ge=0)
    stored_passages: int = Field(ge=0)
    queries: tuple[SearchedQuery, ...] = ()
    services: tuple[str, ...] = ()
    evidence_found: int = Field(ge=0)
    documents_read: int = Field(ge=0)
    failures: int = Field(ge=0)


class StageOption(ContractModel):
    id: uuid.UUID
    ordinal: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=300)


class ComposeFocus(ContractModel):
    discipline: Discipline
    title: str = Field(min_length=1, max_length=HEADING_MAX_CHARS)
    stages: list[StageOption] = Field(default_factory=list)

    @model_validator(mode="after")
    def _stages_once_each(self) -> Self:
        if len({stage.id for stage in self.stages}) != len(self.stages):
            raise ValueError("each process stage is offered once")
        return self


class ComposeRequest(ContractModel):
    question: str = Field(min_length=2, max_length=QUESTION_MAX_CHARS)
    language: AnswerLanguage = CANONICAL_LANGUAGE
    craft: CraftRef | None
    candidates: list[ComposeCandidate] = Field(default_factory=list)
    searched: ResearchSummary
    focus: ComposeFocus | None = None

    @field_validator("language")
    @classmethod
    def _composes_canonical_text(cls, language: str) -> str:
        if language != CANONICAL_LANGUAGE:
            raise ValueError(
                f"the composer writes and checks {CANONICAL_LANGUAGE} sentences; translate them afterwards "
                "with services.answer_translation"
            )
        return language

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        ids = [c.id for c in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate ids are unique")
        if self.searched.craft != self.craft:
            raise ValueError("the research summary belongs to the request's craft")
        return self

    @property
    def allowed(self) -> dict[str, ComposeCandidate]:
        return {c.id: c for c in self.candidates}


class QuotedSpan(ContractModel):
    ref: str = Field(min_length=3, max_length=EVIDENCE_ID_MAX_CHARS)
    text: str = Field(min_length=QUOTE_MIN_CHARS, max_length=QUOTE_MAX_CHARS)


class ComposedSentence(ContractModel):
    text: str = Field(min_length=1, max_length=SENTENCE_MAX_CHARS)
    claim_ids: list[uuid.UUID] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    spans: list[QuotedSpan] = Field(default_factory=list)

    @property
    def cited_ids(self) -> list[str]:
        return [str(c) for c in self.claim_ids] + list(self.evidence_ids)


class ComposedSection(ContractModel):
    heading: str = Field(min_length=1, max_length=HEADING_MAX_CHARS)
    sentences: list[ComposedSentence] = Field(min_length=1)


class ComposedAnswer(ContractModel):
    sections: list[ComposedSection] = Field(default_factory=list)
    open_questions: list[ComposedSentence] = Field(default_factory=list)
    stage_ids: list[uuid.UUID] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list, max_length=FOLLOW_UPS_MAX)
    not_enough_evidence: ResearchSummary | None = None

    @model_validator(mode="after")
    def _answers_or_says_why_not(self) -> Self:
        answered = bool(self.sections or self.open_questions or self.stage_ids)
        if answered == (self.not_enough_evidence is not None):
            raise ValueError("an answer shows something cited or a not-enough-evidence summary, never both")
        if len(set(self.stage_ids)) != len(self.stage_ids):
            raise ValueError("an answer chooses each process stage once")
        return self


class SentenceViolation(ContractModel):
    kind: ViolationKind
    detail: str


def sentence_violations(
    sentence: ComposedSentence, allowed: Mapping[str, ComposeCandidate]
) -> list[SentenceViolation]:
    cited = sentence.cited_ids
    if not cited:
        return [SentenceViolation(kind="UNCITED", detail="the sentence cites nothing")]
    found = [SentenceViolation(kind="UNKNOWN_ID", detail=i) for i in cited if i not in allowed]
    if not sentence.spans:
        found.append(SentenceViolation(kind="UNQUOTED", detail="the sentence quotes no source"))
    verified: list[str] = []
    span_problems: list[SentenceViolation] = []
    for span in sentence.spans:
        problem = _span_problem(span, cited, allowed)
        if problem is not None:
            span_problems.append(SentenceViolation(kind=problem, detail=span.ref))
        elif span.ref in allowed:
            verified.append(span.text)
    found += [
        SentenceViolation(kind="UNSUPPORTED_FIGURE", detail=figure)
        for figure in unsupported_figures(sentence.text, verified)
    ]
    if verified and quote_overlap(sentence.text, verified) < QUOTE_OVERLAP_MIN:
        found.append(SentenceViolation(kind="UNRELATED_QUOTE", detail="the quotes do not carry its wording"))
    return found + span_problems


def _span_problem(
    span: QuotedSpan, cited: list[str], allowed: Mapping[str, ComposeCandidate]
) -> ViolationKind | None:
    if span.ref not in cited:
        return "SPAN_NOT_CITED"
    if span.ref not in allowed:
        return None
    if trivial_quote(span.text):
        return "TRIVIAL_QUOTE"
    if not any(quote_occurs(span.text, t) for t in allowed[span.ref].cited_texts):
        return "SPAN_NOT_IN_SOURCE"
    return None


def sentence_level(sentence: ComposedSentence, allowed: Mapping[str, ComposeCandidate]) -> str:
    unknown = [i for i in sentence.cited_ids if i not in allowed]
    if unknown:
        raise InvalidInput(f"The sentence cites ids outside the allowed set: {', '.join(unknown)}")
    return weakest_level(allowed[i].level for i in sentence.cited_ids)


def not_enough_evidence_message(summary: ResearchSummary) -> str:
    about = f" about {summary.craft.name}" if summary.craft else ""
    return " ".join([f"There is not enough cited evidence to answer this{about} yet.", *_searched(summary)])


def searched_note(summary: ResearchSummary) -> str:
    return " ".join(_searched(summary))


def _searched(summary: ResearchSummary) -> list[str]:
    parts = [
        f"Searched {_count(summary.stored_claims, 'stored claim')} and "
        f"{_count(summary.stored_passages, 'stored source passage')}.",
    ]
    if summary.queries:
        listed = "; ".join(f'{query.tier} "{query.text}"' for query in summary.queries)
        parts.append(f"Live research ran {_count(len(summary.queries), 'query', 'queries')}: {listed}.")
    else:
        parts.append("No live research ran.")
    if summary.services:
        parts.append(f"Sources searched: {', '.join(summary.services)}.")
    parts.append(
        f"Found {_count(summary.evidence_found, 'item')}, read {_count(summary.documents_read, 'document')}"
        f" and recorded {_count(summary.failures, 'failed request')}."
    )
    return parts


def _count(n: int, singular: str, plural: str | None = None) -> str:
    return f"{n} {singular if n == 1 else plural or singular + 's'}"


@runtime_checkable
class Composer(Protocol):
    async def compose(self, request: ComposeRequest) -> ComposedAnswer: ...
