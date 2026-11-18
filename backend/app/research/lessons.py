from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import DISCIPLINES

from .base import ContractModel
from .blocks import ExplainerSentence, require_facts
from .blocks_learning import QuizBlock
from .citations import AnswerSentence, SourceRef, cited_source_ids
from .crafts import CraftRef
from .explainer import SECTION_ID_PATTERN, SectionId
from .media_refs import MediaRef
from .vocabulary import AnswerLanguage

__all__ = [
    "LESSON_BULLETS_MAX",
    "LESSON_FORMATS",
    "LESSON_SCHEMA_VERSION",
    "LESSON_SECTIONS_MAX",
    "LESSON_SLIDES_MAX",
    "LESSON_TITLE_MAX_CHARS",
    "RELIABILITY_ORDER",
    "SLIDE_KINDS",
    "LessonList",
    "LessonPack",
    "LessonRequest",
    "LessonSummary",
    "ReadingItem",
    "Slide",
    "reading_list",
]

LESSON_SCHEMA_VERSION = 1
SLIDE_KINDS = ("TITLE", "SECTION", "QUIZ", "READING", "SOURCES")
LESSON_FORMATS = ("html", "pptx", "pdf")
LESSON_BULLETS_MAX = 5
LESSON_SLIDES_MAX = 60
LESSON_SECTIONS_MAX = len(DISCIPLINES)
LESSON_TITLE_MAX_CHARS = 120
RELIABILITY_ORDER = ("A", "B", "C", "D")
INLINE = "INLINE"

SlideKind = Literal[*SLIDE_KINDS]


class LessonRequest(ContractModel):
    explainer_id: uuid.UUID
    version: int = Field(ge=1)
    title: str | None = Field(min_length=1, max_length=LESSON_TITLE_MAX_CHARS)
    section_ids: list[SectionId] = Field(min_length=1, max_length=LESSON_SECTIONS_MAX)
    quiz: bool

    @model_validator(mode="after")
    def _each_section_once(self) -> Self:
        if len(set(self.section_ids)) != len(self.section_ids):
            raise ValueError("a lesson takes each section once")
        return self


class Slide(ContractModel):
    number: int = Field(ge=1)
    kind: SlideKind
    title: str = Field(min_length=1, max_length=LESSON_TITLE_MAX_CHARS)
    section_id: str | None = Field(pattern=SECTION_ID_PATTERN)
    block_ids: list[str]
    bullets: list[ExplainerSentence] = Field(max_length=LESSON_BULLETS_MAX)
    image: MediaRef | None
    question: int | None = Field(ge=0)

    @model_validator(mode="after")
    def _what_each_kind_of_slide_holds(self) -> Self:
        section = self.kind == "SECTION"
        holds_section = self.section_id is not None and bool(self.block_ids) and bool(self.bullets)
        if section != holds_section or (not section and self.image is not None):
            raise ValueError(f"slide {self.number} shows a section's cited sentences exactly when it is one")
        if (self.kind == "QUIZ") != (self.question is not None):
            raise ValueError(f"slide {self.number} asks a quiz question exactly when it is a quiz slide")
        if self.image is not None and self.image.display != INLINE:
            raise ValueError(f"slide {self.number} shows only an openly licensed picture")
        require_facts(f"slide {self.number}", self.bullets)
        return self


class ReadingItem(ContractModel):
    source: SourceRef
    cited_by: int = Field(ge=1)


class LessonPack(ContractModel):
    schema_version: Literal[1]
    id: uuid.UUID
    explainer_id: uuid.UUID
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=LESSON_TITLE_MAX_CHARS)
    craft: CraftRef | None
    language: AnswerLanguage
    created_at: AwareDatetime
    slides: list[Slide] = Field(min_length=3, max_length=LESSON_SLIDES_MAX)
    reading_list: list[ReadingItem] = Field(min_length=1)
    quiz: QuizBlock | None
    sources: list[SourceRef]

    @model_validator(mode="after")
    def _slides_in_order_with_their_sources(self) -> Self:
        problems = _slide_order_problems(self.slides, self.quiz)
        shown = _shown_sentences(self.slides, self.quiz)
        if [source.id for source in self.sources] != cited_source_ids(shown):
            problems.append("a lesson lists every cited source once, in order of first citation")
        if self.reading_list != reading_list(self.sources, shown):
            problems.append("a lesson reads its sources by reliability, then by how often they are cited")
        if problems:
            raise ValueError("; ".join(problems))
        return self


class LessonSummary(ContractModel):
    id: uuid.UUID
    title: str = Field(min_length=1, max_length=LESSON_TITLE_MAX_CHARS)
    explainer_id: uuid.UUID
    version: int = Field(ge=1)
    craft: CraftRef | None
    created_at: AwareDatetime
    slide_count: int = Field(ge=3, le=LESSON_SLIDES_MAX)


class LessonList(ContractModel):
    schema_version: Literal[1]
    items: list[LessonSummary]

    @model_validator(mode="after")
    def _newest_first(self) -> Self:
        made = [item.created_at for item in self.items]
        if made != sorted(made, reverse=True):
            raise ValueError("lessons are listed newest first")
        return self


def reading_list(sources: Sequence[SourceRef], shown: Iterable[AnswerSentence]) -> list[ReadingItem]:
    counts: Counter[str] = Counter()
    for sentence in shown:
        counts.update({citation.source_id for citation in sentence.citations})
    first = {source.id: index for index, source in enumerate(sources)}

    def rank(source: SourceRef) -> tuple[int, int, int]:
        tier = RELIABILITY_ORDER.index(source.reliability) if source.reliability else len(RELIABILITY_ORDER)
        return tier, -counts[source.id], first[source.id]

    return [ReadingItem(source=source, cited_by=counts[source.id]) for source in sorted(sources, key=rank)]


def _slide_order_problems(slides: Sequence[Slide], quiz: QuizBlock | None) -> list[str]:
    problems = []
    if [slide.number for slide in slides] != list(range(1, len(slides) + 1)):
        problems.append("slides are numbered 1 to n")
    kinds = [slide.kind for slide in slides]
    questions = len(quiz.questions) if quiz is not None else 0
    expected_tail = ["QUIZ"] * questions + ["READING", "SOURCES"]
    sections = len(kinds) - 1 - len(expected_tail)
    if sections < 1 or kinds != ["TITLE", *["SECTION"] * sections, *expected_tail]:
        problems.append("a lesson runs title, sections, one slide per quiz question, reading, sources")
    asked = [slide.question for slide in slides if slide.kind == "QUIZ"]
    if asked != list(range(questions)):
        problems.append("the quiz slides ask the quiz's questions in order")
    return problems


def _shown_sentences(slides: Sequence[Slide], quiz: QuizBlock | None) -> list[AnswerSentence]:
    bullets: list[AnswerSentence] = [sentence for slide in slides for sentence in slide.bullets]
    return bullets + (list(quiz.cited_sentences()) if quiz is not None else [])
