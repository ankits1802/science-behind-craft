from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel, HttpsUrl, PartialDate
from .blocks import BlockBase, ExplainerSentence
from .citations import AnswerSentence
from .crafts import CraftRef
from .evidence import personal_data_in
from .media_refs import MediaRef
from .quotes import figures_in
from .vocabulary import AnswerLanguage

__all__ = [
    "AUDIENCES",
    "EXPERT_SEATS",
    "QUIZ_MAX_QUESTIONS",
    "ArtisanQuote",
    "ArtisanRef",
    "ArtisanVoiceBlock",
    "CompareBlock",
    "CompareRow",
    "DesignRef",
    "DesignsBlock",
    "ExpertDifference",
    "ExpertViewBlock",
    "InPracticeBlock",
    "OpenQuestion",
    "OpenQuestionsBlock",
    "PracticeNote",
    "QuizBlock",
    "QuizQuestion",
]

EXPERT_SEATS = (
    "CHEMIST",
    "PHYSICIST",
    "MATERIALS_SCIENTIST",
    "TECHNOLOGIST",
    "GEOLOGIST",
    "HYDROLOGIST",
    "SOIL_SCIENTIST",
    "CLIMATOLOGIST",
    "ECOLOGIST",
    "BOTANIST",
    "TOXICOLOGIST",
    "HISTORIAN",
    "ANTHROPOLOGIST",
    "ECONOMIST",
    "DESIGN_HISTORIAN",
    "CONSERVATOR",
    "POLICY_EXPERT",
    "ARTISAN",
)
AUDIENCES = ("ARTISAN", "STUDENT", "DESIGNER", "POLICY", "NGO", "CONSERVATOR")
QUIZ_MAX_QUESTIONS = 10

ExpertSeat = Literal[*EXPERT_SEATS]
Audience = Literal[*AUDIENCES]


class ExpertDifference(ContractModel):
    seat: ExpertSeat
    this_view: ExplainerSentence
    other_view: ExplainerSentence


class ExpertViewBlock(BlockBase):
    kind: Literal["expert_view"]
    version: Literal[1]
    seat: ExpertSeat
    take: list[ExplainerSentence] = Field(min_length=1)
    agrees_with: list[ExpertSeat]
    differs: list[ExpertDifference]

    @model_validator(mode="after")
    def _never_differs_with_itself(self) -> Self:
        others = [*self.agrees_with, *(difference.seat for difference in self.differs)]
        if self.seat in others or len(set(self.agrees_with)) != len(self.agrees_with):
            raise ValueError(f"expert view {self.id} names each other seat once and never its own")
        return self

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        yield from self.take
        for difference in self.differs:
            yield difference.this_view
            yield difference.other_view


class CompareRow(ContractModel):
    aspect: str = Field(min_length=1, max_length=120)
    left: ExplainerSentence | None
    right: ExplainerSentence | None


class CompareBlock(BlockBase):
    kind: Literal["compare"]
    version: Literal[1]
    crafts: list[CraftRef] = Field(min_length=2, max_length=2)
    rows: list[CompareRow] = Field(min_length=1)
    piece_ids: list[uuid.UUID]

    @model_validator(mode="after")
    def _two_different_crafts(self) -> Self:
        if self.crafts[0].slug == self.crafts[1].slug:
            raise ValueError(f"compare {self.id} sets two different crafts side by side")
        return self

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for row in self.rows:
            yield from (side for side in (row.left, row.right) if side is not None)


class PracticeNote(ContractModel):
    audience: Audience
    sentences: list[ExplainerSentence] = Field(min_length=1)


class InPracticeBlock(BlockBase):
    kind: Literal["in_practice"]
    version: Literal[1]
    notes: list[PracticeNote] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_note_per_audience(self) -> Self:
        audiences = [note.audience for note in self.notes]
        if len(set(audiences)) != len(audiences):
            raise ValueError(f"in practice {self.id} has one note per audience")
        return self

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for note in self.notes:
            yield from note.sentences


class QuizQuestion(ContractModel):
    prompt: str = Field(min_length=1, max_length=300)
    options: list[str] = Field(min_length=2, max_length=5)
    answer: int = Field(ge=0)
    explanation: ExplainerSentence

    @model_validator(mode="after")
    def _the_key_is_an_option(self) -> Self:
        if self.answer >= len(self.options) or len(set(self.options)) != len(self.options):
            raise ValueError(f"quiz question {self.prompt!r} keys one of its distinct options")
        return self


class QuizBlock(BlockBase):
    kind: Literal["quiz"]
    version: Literal[1]
    questions: list[QuizQuestion] = Field(min_length=1, max_length=QUIZ_MAX_QUESTIONS)

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for question in self.questions:
            yield question.explanation


class OpenQuestion(ContractModel):
    sentence: ExplainerSentence
    how_to_find_out: str | None = Field(max_length=300)

    @model_validator(mode="after")
    def _a_hypothesis_and_a_figure_free_way_to_find_out(self) -> Self:
        if self.sentence.level != "HYPOTHESIS":
            raise ValueError(f"open question {self.sentence.id} is a hypothesis")
        if self.how_to_find_out and figures_in(self.how_to_find_out):
            raise ValueError(f"open question {self.sentence.id} suggests a way to find out with no figures")
        return self


class OpenQuestionsBlock(BlockBase):
    kind: Literal["open_questions"]
    version: Literal[1]
    items: list[OpenQuestion] = Field(min_length=1)

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for item in self.items:
            yield item.sentence


class ArtisanRef(ContractModel):
    name: str = Field(min_length=1, max_length=200)
    credentials: list[str]
    village: str | None = Field(max_length=200)
    district: str | None = Field(max_length=200)
    state: str | None = Field(max_length=200)
    address: str | None = Field(max_length=300)


class ArtisanQuote(ContractModel):
    artisan: ArtisanRef
    quote: str = Field(min_length=1, max_length=600)
    language: AnswerLanguage
    source_id: str = Field(min_length=1)
    locator: str = Field(min_length=1, max_length=120)


class ArtisanVoiceBlock(BlockBase):
    kind: Literal["artisan_voice"]
    version: Literal[1]
    quotes: list[ArtisanQuote] = Field(min_length=1)

    @model_validator(mode="after")
    def _no_contact_or_identity_numbers(self) -> Self:
        for quote in self.quotes:
            artisan = quote.artisan
            texts = [quote.quote, artisan.name, *artisan.credentials]
            texts += [t for t in (artisan.village, artisan.district, artisan.state, artisan.address) if t]
            if any(personal_data_in(text) for text in texts):
                raise ValueError(f"artisan voice {self.id} never shows a phone, email or identity number")
        return self

    def direct_source_ids(self) -> Iterator[str]:
        for quote in self.quotes:
            yield quote.source_id


class DesignRef(ContractModel):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    workshop: str | None = Field(max_length=300)
    made_on: PartialDate | None
    url: HttpsUrl
    image: MediaRef | None
    source_id: str = Field(min_length=1)


class DesignsBlock(BlockBase):
    kind: Literal["designs"]
    version: Literal[1]
    designs: list[DesignRef] = Field(min_length=1)

    def direct_source_ids(self) -> Iterator[str]:
        for design in self.designs:
            yield design.source_id
