from __future__ import annotations

from collections.abc import Iterator
from typing import ClassVar, Literal, Self

from pydantic import Field, model_validator

from .blocks import SENTENCE, BlockBase, ExplainerSentence, SentenceSpec, require_facts
from .blocks_signature import SignatureBlock
from .citations import AnswerSentence
from .composition import LEDE_SENTENCES_MAX, LEDE_SENTENCES_MIN
from .crafts import QUESTION_MAX_CHARS

__all__ = ["LEDE_BLOCK_ID", "LEDE_KIND", "LedeBlock"]

LEDE_KIND = "lede"
LEDE_BLOCK_ID = "lede"


class LedeBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (("sentences", [SENTENCE]),)

    kind: Literal["lede"]
    version: Literal[1]
    headline: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    sentences: list[ExplainerSentence] = Field(min_length=LEDE_SENTENCES_MIN, max_length=LEDE_SENTENCES_MAX)
    figure: SignatureBlock | None

    @model_validator(mode="after")
    def _the_answer_to_this_question(self) -> Self:
        if self.id != LEDE_BLOCK_ID:
            raise ValueError(f"the lede's id is {LEDE_BLOCK_ID!r}, not {self.id!r}")
        if self.reuse is not None:
            raise ValueError("a lede is written for its question and never reused")
        require_facts("the lede", self.sentences)
        return self

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        yield from self.sentences
        if self.figure is not None:
            yield from self.figure.cited_sentences()

    def direct_source_ids(self) -> Iterator[str]:
        if self.figure is not None:
            yield from self.figure.direct_source_ids()

    def shown_labels(self) -> list[str]:
        return self.figure.shown_labels() if self.figure is not None else []
