from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import Field, model_validator

from app.models.enums import DISCIPLINES, SECTION_STATUSES
from app.models.section_proposals import SECTION_PROPOSAL_STATUSES, SECTION_REVIEW_NOTE_CHARS

from .article_sections import SectionSentence
from .base import ContractModel
from .knowledge_writes import ProposalSubject
from .vocabulary import Discipline

__all__ = [
    "APPROVED_STATUS",
    "FAITHFUL",
    "FIELD",
    "HELD",
    "PENDING_STATUS",
    "REFUSED",
    "REFUSED_STATUS",
    "REJECTED_STATUS",
    "SECTIONS_MAX",
    "SECTION_CHECKS",
    "SECTION_CLAIMS_PER_SENTENCE_MAX",
    "SECTION_NOTE_MAX_CHARS",
    "SECTION_OUTCOMES",
    "SECTION_SENTENCES_MAX",
    "SECTION_TICKET_KIND",
    "SENTENCES",
    "STATED",
    "STORED",
    "WRITTEN",
    "PublishedSection",
    "SectionCheck",
    "SectionOutcome",
    "SectionPart",
    "SectionTicket",
    "first_refusal",
]

SECTIONS_MAX = len(DISCIPLINES)
SECTION_SENTENCES_MAX = 24
SECTION_CLAIMS_PER_SENTENCE_MAX = 8
SECTION_NOTE_MAX_CHARS = SECTION_REVIEW_NOTE_CHARS
PENDING_STATUS, APPROVED_STATUS, REJECTED_STATUS, REFUSED_STATUS = SECTION_PROPOSAL_STATUSES
HELD, FIELD, SENTENCES, STATED, FAITHFUL = SECTION_CHECKS = (
    "HELD",
    "FIELD",
    "SENTENCES",
    "STATED",
    "FAITHFUL",
)
STORED, WRITTEN, REFUSED = SECTION_OUTCOMES = ("STORED", "WRITTEN", "REFUSED")
MANY_FACTS = "a sentence cites at most {most} facts"
SECTION_TICKET_KIND = "SECTION"
SECTION_TICKET_SCHEMA_VERSION = 1
BECAME_ON_APPROVAL = "a section proposal became a published section only once it was approved"


class SectionPart(ContractModel):
    field: Discipline
    sentences: list[SectionSentence] = Field(min_length=1, max_length=SECTION_SENTENCES_MAX)
    note: str | None = Field(default=None, min_length=1, max_length=SECTION_NOTE_MAX_CHARS)

    @model_validator(mode="after")
    def _few_facts_a_sentence(self) -> Self:
        if any(len(sentence.claim_ids) > SECTION_CLAIMS_PER_SENTENCE_MAX for sentence in self.sentences):
            raise ValueError(MANY_FACTS.format(most=SECTION_CLAIMS_PER_SENTENCE_MAX))
        return self

    def claim_ids(self) -> list[uuid.UUID]:
        return list(dict.fromkeys(claim for sentence in self.sentences for claim in sentence.claim_ids))


class SectionCheck(ContractModel):
    check: Literal[*SECTION_CHECKS]
    passed: bool
    reasons: list[str]


class SectionOutcome(ContractModel):
    outcome: Literal[*SECTION_OUTCOMES]
    proposal_id: uuid.UUID
    status: Literal[*SECTION_PROPOSAL_STATUSES]
    checks: list[SectionCheck]
    message: str


class PublishedSection(ContractModel):
    version: int = Field(ge=1)
    status: Literal[*SECTION_STATUSES]
    page_url: str | None = None


class SectionTicket(ContractModel):
    schema_version: Literal[1] = SECTION_TICKET_SCHEMA_VERSION
    proposal_id: uuid.UUID
    kind: Literal["SECTION"] = SECTION_TICKET_KIND
    status: Literal[*SECTION_PROPOSAL_STATUSES]
    subject: ProposalSubject
    field: Discipline
    sentences: list[SectionSentence] = Field(min_length=1)
    checks: list[SectionCheck]
    task_key: str | None = None
    note: str | None = None
    proposed_at: datetime
    reviewed_at: datetime | None = None
    review_note: str | None = None
    section: PublishedSection | None = None
    message: str

    @model_validator(mode="after")
    def _a_section_only_once_approved(self) -> Self:
        if self.section is not None and self.status != APPROVED_STATUS:
            raise ValueError(BECAME_ON_APPROVAL)
        return self


def first_refusal(checks: list[SectionCheck]) -> SectionCheck | None:
    return next((check for check in checks if not check.passed), None)
