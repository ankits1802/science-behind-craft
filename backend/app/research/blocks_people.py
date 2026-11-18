from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import ClassVar, Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel, HttpsUrl, PartialDate
from .blocks import SENTENCE, BlockBase, ExplainerSentence, SentenceSpec, require_facts
from .citations import AnswerSentence, Citation
from .media_refs import MediaRef
from .quotes import figures_in
from .voices import VoiceQuote

__all__ = [
    "AUDIENCES",
    "EXPERT_SEATS",
    "ArtisanVoiceBlock",
    "DesignRef",
    "DesignsBlock",
    "ExpertDifference",
    "ExpertViewBlock",
    "InPracticeBlock",
    "OpenQuestion",
    "OpenQuestionsBlock",
    "PracticeNote",
    "expert_pairing_problems",
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

ExpertSeat = Literal[*EXPERT_SEATS]
Audience = Literal[*AUDIENCES]


class ExpertDifference(ContractModel):
    seat: ExpertSeat
    this_view: ExplainerSentence
    other_view: ExplainerSentence

    @model_validator(mode="after")
    def _two_views_from_different_evidence(self) -> Self:
        mine, theirs = self.this_view, self.other_view
        if _claims_of(mine) & _claims_of(theirs) or _sources_of(mine) & _sources_of(theirs):
            raise ValueError(f"the difference with {self.seat} rests each view on its own claims and sources")
        return self


class ExpertViewBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (
        ("take", [SENTENCE]),
        ("differs", [(("this_view", SENTENCE), ("other_view", SENTENCE))]),
    )

    kind: Literal["expert_view"]
    version: Literal[1]
    seat: ExpertSeat
    take: list[ExplainerSentence] = Field(min_length=1)
    agrees_with: list[ExpertSeat]
    differs: list[ExpertDifference]

    @model_validator(mode="after")
    def _never_differs_with_itself(self) -> Self:
        require_facts(f"expert view {self.id}", list(self.cited_sentences()))
        others = [*self.agrees_with, *(difference.seat for difference in self.differs)]
        if self.seat in others or len(set(others)) != len(others):
            raise ValueError(f"expert view {self.id} names each other seat once and never its own")
        return self


def expert_pairing_problems(blocks: Sequence[BlockBase]) -> list[str]:
    views = [block for block in blocks if isinstance(block, ExpertViewBlock)]
    by_seat = {view.seat: view for view in views}
    problems = [] if len(by_seat) == len(views) else ["each seat gives one view per section"]
    for view in views:
        for seat in view.agrees_with:
            other = by_seat.get(seat)
            if other is None or view.seat not in other.agrees_with:
                problems.append(f"{view.seat} and {seat} agree only when both views say so")
        for difference in view.differs:
            mirror = _difference_with(by_seat.get(difference.seat), view.seat)
            if mirror is None or not _mirrored(difference, mirror):
                problems.append(f"{view.seat} and {difference.seat} differ only when both views state it")
    return problems


def _difference_with(view: ExpertViewBlock | None, seat: str) -> ExpertDifference | None:
    if view is None:
        return None
    return next((difference for difference in view.differs if difference.seat == seat), None)


def _mirrored(one: ExpertDifference, other: ExpertDifference) -> bool:
    return _claims_of(one.this_view) == _claims_of(other.other_view) and _claims_of(
        one.other_view
    ) == _claims_of(other.this_view)


def _claims_of(sentence: AnswerSentence) -> frozenset[str]:
    return frozenset(citation.claim_id for citation in sentence.citations)


def _sources_of(sentence: AnswerSentence) -> frozenset[str]:
    return frozenset(citation.source_id for citation in sentence.citations)


class PracticeNote(ContractModel):
    audience: Audience
    sentences: list[ExplainerSentence] = Field(min_length=1)


class InPracticeBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (("notes", [(("sentences", [SENTENCE]),)]),)

    kind: Literal["in_practice"]
    version: Literal[1]
    notes: list[PracticeNote] = Field(min_length=1)

    @model_validator(mode="after")
    def _one_note_per_audience(self) -> Self:
        audiences = [note.audience for note in self.notes]
        if len(set(audiences)) != len(audiences):
            raise ValueError(f"in practice {self.id} has one note per audience")
        return self


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
    SENTENCES: ClassVar[SentenceSpec] = (("items", [(("sentence", SENTENCE),)]),)

    kind: Literal["open_questions"]
    version: Literal[1]
    items: list[OpenQuestion] = Field(min_length=1)


class ArtisanVoiceBlock(BlockBase):
    kind: Literal["artisan_voice"]
    version: Literal[2]
    quotes: list[VoiceQuote]
    removed: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _every_block_carries_its_evidence(self) -> Self:
        if not self.quotes and self.removed == 0:
            raise ValueError(f"artisan voice {self.id} quotes nobody, so it is not shown")
        ids = [quote.item_id for quote in self.quotes]
        if len(ids) != len(set(ids)):
            raise ValueError(f"artisan voice {self.id} quotes an item twice")
        return self

    def citations(self) -> Iterator[Citation]:
        for quote in self.quotes:
            yield from quote.corroborated_by

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
