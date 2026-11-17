from __future__ import annotations

from collections.abc import Iterator
from typing import Self

from pydantic import Field, model_validator

from app.research.base import ContractModel
from app.research.vocabulary import Discipline

from .fields import ClaimIds, SentenceText
from .limits import (
    KEY_FACTS_MAX,
    LEDE_SENTENCES_MAX,
    LEDE_SENTENCES_MIN,
    SECTION_SENTENCES_MAX,
    SECTION_SENTENCES_MIN,
)

__all__ = ["KeyFact", "Overview", "OverviewSection", "OverviewSentence"]


class OverviewSentence(ContractModel):
    text: SentenceText
    claim_ids: ClaimIds


class KeyFact(ContractModel):
    label: str = Field(min_length=1, max_length=60)
    value: str = Field(min_length=1, max_length=200)
    claim_ids: ClaimIds


class OverviewSection(ContractModel):
    discipline: Discipline
    sentences: list[OverviewSentence] = Field(
        min_length=SECTION_SENTENCES_MIN, max_length=SECTION_SENTENCES_MAX
    )


class Overview(ContractModel):
    lede: list[OverviewSentence] = Field(min_length=LEDE_SENTENCES_MIN, max_length=LEDE_SENTENCES_MAX)
    key_facts: list[KeyFact] = Field(min_length=1, max_length=KEY_FACTS_MAX)
    sections: list[OverviewSection] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_section_per_discipline(self) -> Self:
        disciplines = [section.discipline for section in self.sections]
        if len(disciplines) != len(set(disciplines)):
            raise ValueError("the overview has one section per discipline")
        return self

    def located_sentences(self) -> Iterator[tuple[str, OverviewSentence]]:
        for index, sentence in enumerate(self.lede):
            yield f"overview.lede.{index}", sentence
        for section in self.sections:
            for index, sentence in enumerate(section.sentences):
                yield f"overview.{section.discipline}.{index}", sentence
