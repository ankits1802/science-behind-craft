from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from types import MappingProxyType
from typing import Literal, Self

from pydantic import Field, model_validator

from app.models.page_proposals import DRAWN_SIDES

from .base import ContractModel, absent
from .page_changes import ChapterChanges
from .page_proposals import COMPONENT, FACT, LAYOUT, PICTURE, SECTION, STRUCTURE, PageSubject
from .review_queue import (
    APPROVE,
    COMPONENTS,
    FACTS,
    IMAGES,
    LAYOUTS,
    REASON_MAX_CHARS,
    REASON_MIN_CHARS,
    REJECT,
    SECTIONS,
    STRUCTURE as STRUCTURE_QUEUE,
)
from .review_queue_items import Proposer

__all__ = [
    "AFTER",
    "APPLIED",
    "APPROVED",
    "BEFORE",
    "CHAPTER_SCOPE",
    "CLOSED",
    "COMPONENT_SCOPE",
    "DECIDED_ORDER",
    "PAGES",
    "PAGE_ACTIONS",
    "PAGE_REVIEW_SCHEMA_VERSION",
    "PAGE_SCOPE",
    "PART_OUTCOMES",
    "PART_QUEUES",
    "PART_QUEUE_KINDS",
    "PART_STATES",
    "REFUSED",
    "REJECTED",
    "SCOPES",
    "SKIPPED",
    "TITLE_MAX_CHARS",
    "WAITING",
    "DrawAsk",
    "DrawnPictureView",
    "PageDecision",
    "PageDecisionBody",
    "PageDecisionReply",
    "PageDrawing",
    "PageProposalLine",
    "PageProposalList",
    "PageProposalView",
    "PageReviewNote",
    "PageScope",
    "PartOutcome",
    "PartView",
    "ProposalPart",
    "parts_in_scope",
    "proposal_line",
    "scope_words",
]

PAGE_REVIEW_SCHEMA_VERSION = 1
PAGES = "PAGES"
BEFORE, AFTER = DRAWN_SIDES
SCOPES = ("PAGE", "CHAPTER", "COMPONENT")
PART_STATES = ("WAITING", "APPROVED", "REJECTED", "CLOSED")
PART_OUTCOMES = ("APPLIED", "REFUSED", "SKIPPED")
PAGE_SCOPE, CHAPTER_SCOPE, COMPONENT_SCOPE = SCOPES
WAITING, APPROVED, REJECTED, CLOSED = PART_STATES
APPLIED, REFUSED, SKIPPED = PART_OUTCOMES
PAGE_ACTIONS = (APPROVE, REJECT)
TITLE_MAX_CHARS = 300
PART_QUEUES: Mapping[str, str] = MappingProxyType(
    {
        FACT: FACTS,
        STRUCTURE: STRUCTURE_QUEUE,
        PICTURE: IMAGES,
        COMPONENT: COMPONENTS,
        LAYOUT: LAYOUTS,
        SECTION: SECTIONS,
    }
)
DECIDED_ORDER: tuple[str, ...] = tuple(PART_QUEUES)
PART_QUEUE_KINDS: tuple[str, ...] = tuple(PART_QUEUES.values())
CHAPTER_NEEDED = "A chapter's decision names its chapter, and only a chapter's decision names one."
LABEL_NEEDED = "A component's decision names its label, and only a component's decision names one."
REASON_NEEDED = "A rejection gives its reason in words, at least three characters, for the contributor."
WHOLE_PAGE = "the whole page"
CHAPTER_WORDS = "the chapter {chapter}"
COMPONENT_WORDS = "the component {label}"

PartKind = Literal[*DECIDED_ORDER]
PartQueue = Literal[*PART_QUEUE_KINDS]
Scope = Literal[*SCOPES]
Side = Literal[*DRAWN_SIDES]


class ProposalPart(ContractModel):
    part: PartKind
    kind: PartQueue
    id: uuid.UUID
    chapter: str | None = None
    label: str | None = None
    title: str = Field(max_length=TITLE_MAX_CHARS)


class PartView(ProposalPart):
    state: Literal[*PART_STATES]


class PageScope(ContractModel):
    scope: Scope = PAGE_SCOPE
    chapter: str | None = Field(default=None, min_length=1, max_length=40)
    label: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def _names_its_part(self) -> Self:
        if (self.chapter is not None) != (self.scope == CHAPTER_SCOPE):
            raise ValueError(CHAPTER_NEEDED)
        if (self.label is not None) != (self.scope == COMPONENT_SCOPE):
            raise ValueError(LABEL_NEEDED)
        return self


class PageDecisionBody(PageScope):
    action: Literal[*PAGE_ACTIONS]
    note: str | None = Field(default=None, min_length=1, max_length=REASON_MAX_CHARS)

    @model_validator(mode="after")
    def _a_rejection_says_why(self) -> Self:
        if self.action == REJECT and (self.note is None or len(self.note) < REASON_MIN_CHARS):
            raise ValueError(REASON_NEEDED)
        return self

    def scoped(self) -> PageScope:
        return PageScope(scope=self.scope, chapter=self.chapter, label=self.label)


class PartOutcome(ContractModel):
    part: PartKind
    kind: PartQueue
    id: uuid.UUID
    title: str
    outcome: Literal[*PART_OUTCOMES]
    message: str


class PageDecision(ContractModel):
    action: Literal[*PAGE_ACTIONS]
    scope: Scope
    chapter: str | None = Field(default=None, exclude_if=absent)
    label: str | None = Field(default=None, exclude_if=absent)
    note: str | None = None
    decided_at: datetime
    outcomes: list[PartOutcome]


class DrawnPictureView(ContractModel):
    side: Side
    name: str
    caption: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    url: str


class PageProposalView(ContractModel):
    schema_version: Literal[1] = PAGE_REVIEW_SCHEMA_VERSION
    id: uuid.UUID
    subject: PageSubject
    subject_name: str
    page_url: str
    origin: str
    proposer: Proposer | None = None
    created_at: datetime
    waiting: int = Field(ge=0)
    parts: list[PartView]
    chapters: list[ChapterChanges]
    pictures: list[DrawnPictureView]
    drawable: list[Side]
    decisions: list[PageDecision]
    whole: bool = True


class PageProposalList(ContractModel):
    schema_version: Literal[1] = PAGE_REVIEW_SCHEMA_VERSION
    proposals: list[PageProposalView]


class PageProposalLine(ContractModel):
    id: uuid.UUID
    subject: PageSubject
    subject_name: str
    page_url: str
    created_at: datetime
    waiting: int = Field(ge=0)
    parts: int = Field(ge=0)
    pictures: int = Field(ge=0)
    chapters: list[ChapterChanges]


class PageDrawing(ContractModel):
    side: Side
    drawn: bool
    message: str
    pictures: list[DrawnPictureView]
    problems: list[str] = Field(default_factory=list)


class DrawAsk(ContractModel):
    side: Side


class PageDecisionReply(ContractModel):
    schema_version: Literal[1] = PAGE_REVIEW_SCHEMA_VERSION
    decision: PageDecision
    message: str
    open: bool


class PageReviewNote(ContractModel):
    proposal_id: uuid.UUID
    subject: PageSubject
    action: Literal[*PAGE_ACTIONS]
    scope: Scope
    chapter: str | None = Field(default=None, exclude_if=absent)
    label: str | None = Field(default=None, exclude_if=absent)
    note: str | None
    decided_at: datetime
    outcomes: list[PartOutcome]


def proposal_line(view: PageProposalView) -> PageProposalLine:
    return PageProposalLine(
        id=view.id,
        subject=view.subject,
        subject_name=view.subject_name,
        page_url=view.page_url,
        created_at=view.created_at,
        waiting=view.waiting,
        parts=len(view.parts),
        pictures=len(view.pictures),
        chapters=[chapter.model_copy(update={"changes": []}) for chapter in view.chapters],
    )


def parts_in_scope(parts: Sequence[ProposalPart], scope: PageScope) -> list[ProposalPart]:
    chosen = [part for part in parts if _within(part, scope)]
    return sorted(chosen, key=lambda part: DECIDED_ORDER.index(part.part))


def scope_words(scope: PageScope) -> str:
    if scope.scope == CHAPTER_SCOPE:
        return CHAPTER_WORDS.format(chapter=scope.chapter)
    if scope.scope == COMPONENT_SCOPE:
        return COMPONENT_WORDS.format(label=scope.label)
    return WHOLE_PAGE


def _within(part: ProposalPart, scope: PageScope) -> bool:
    if scope.scope == CHAPTER_SCOPE:
        return part.chapter is not None and part.chapter == scope.chapter
    if scope.scope == COMPONENT_SCOPE:
        return part.label is not None and part.label == scope.label
    return True
