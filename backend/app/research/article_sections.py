from __future__ import annotations

import uuid
from html import escape
from typing import Literal, Self

from pydantic import Field, model_validator

from app.models.enums import SECTION_STATUSES

from .base import ContractModel
from .vocabulary import Discipline

__all__ = [
    "ARTICLE_SECTION_SCHEMA_VERSION",
    "SECTION_SUBJECT_KINDS",
    "ArticleSection",
    "SectionSentence",
    "tagged_section",
]

ARTICLE_SECTION_SCHEMA_VERSION = 1
SECTION_SUBJECT_KINDS = ("craft", "category")
SECTION_SENTENCE_MAX_CHARS = 1000
SUBJECT_SLUG_MAX_CHARS = 200

SectionStatus = Literal[*SECTION_STATUSES]
SectionSubjectKind = Literal[*SECTION_SUBJECT_KINDS]


class SectionSentence(ContractModel):
    text: str = Field(min_length=1, max_length=SECTION_SENTENCE_MAX_CHARS)
    claim_ids: list[uuid.UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def _each_claim_once(self) -> Self:
        if len(set(self.claim_ids)) != len(self.claim_ids):
            raise ValueError("a sentence cites each claim once")
        return self


class ArticleSection(ContractModel):
    schema_version: Literal[1] = ARTICLE_SECTION_SCHEMA_VERSION
    subject_kind: SectionSubjectKind
    subject_slug: str = Field(min_length=1, max_length=SUBJECT_SLUG_MAX_CHARS, pattern=r"^[A-Za-z0-9-]+$")
    field: Discipline
    version: int = Field(ge=1)
    status: SectionStatus
    sentences: list[SectionSentence] = Field(min_length=1)


def tagged_section(section: ArticleSection) -> str:
    body = " ".join(_tagged_sentence(sentence) for sentence in section.sentences)
    return (
        f'<section {section.subject_kind}="{section.subject_slug}" field="{section.field.lower()}" '
        f'version="{section.version}">{body}</section>'
    )


def _tagged_sentence(sentence: SectionSentence) -> str:
    marks = " ".join(f"[c:{claim_id}]" for claim_id in sentence.claim_ids)
    return f"{escape(sentence.text, quote=False)} {marks}"
