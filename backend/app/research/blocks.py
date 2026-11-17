from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator, Mapping
from itertools import pairwise
from typing import Any, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import IMAGE_RELEVANCE

from .base import ContractModel
from .citations import AnswerSentence, Citation
from .crafts import CraftRef
from .media_refs import MediaRef
from .quotes import quote_occurs
from .terms import TermSpan, span_problems
from .vocabulary import FACT_LEVELS, MaterialKind, MaterialRole, ShownLevel, StageType, weakest_level

__all__ = [
    "BLOCK_ID_MAX_CHARS",
    "BLOCK_ID_PATTERN",
    "IMAGES_MAX",
    "IMAGE_RELEVANCE",
    "BlockBase",
    "ExplainerSentence",
    "ImageItem",
    "ImagesBlock",
    "LadderCondition",
    "LadderMaterial",
    "LadderStage",
    "ProcessLadderBlock",
    "ProseBlock",
    "ReuseMarker",
    "payload_sentences",
    "with_payload_sentences",
]

BLOCK_ID_MAX_CHARS = 80
BLOCK_ID_PATTERN = r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$"
IMAGES_MAX = 8

ImageRelevance = Literal[*IMAGE_RELEVANCE]
SentenceChange = Callable[[Mapping[str, Any]], dict[str, Any]]
LADDER_KIND = "process_ladder"


class ReuseMarker(ContractModel):
    piece_id: uuid.UUID
    stored_at: AwareDatetime


class ExplainerSentence(AnswerSentence):
    terms: list[TermSpan]

    @model_validator(mode="after")
    def _terms_mark_the_shown_text(self) -> Self:
        problems = span_problems(self.text, self.terms)
        if problems:
            raise ValueError(f"sentence {self.id}: {'; '.join(problems)}")
        return self


class BlockBase(ContractModel):
    id: str = Field(min_length=1, max_length=BLOCK_ID_MAX_CHARS, pattern=BLOCK_ID_PATTERN)
    kind: str
    version: int
    reuse: ReuseMarker | None

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        yield from ()

    def citations(self) -> Iterator[Citation]:
        for sentence in self.cited_sentences():
            yield from sentence.citations

    def direct_source_ids(self) -> Iterator[str]:
        yield from ()

    def illustrated_claim_ids(self) -> set[str]:
        return set()

    def cited_claim_ids(self) -> set[str]:
        return {citation.claim_id for citation in self.citations()}

    def cited_source_ids(self) -> list[str]:
        ordered = dict.fromkeys(citation.source_id for citation in self.citations())
        ordered.update(dict.fromkeys(self.direct_source_ids()))
        return list(ordered)

    def cites_datasets(self) -> bool:
        return False

    @model_validator(mode="after")
    def _every_block_carries_its_evidence(self) -> Self:
        if not (self.cited_source_ids() or self.illustrated_claim_ids() or self.cites_datasets()):
            raise ValueError(f"block {self.id} cites nothing, so it is not shown")
        return self


class ProseBlock(BlockBase):
    kind: Literal["prose"]
    version: Literal[1]
    sentences: list[ExplainerSentence] = Field(min_length=1)

    @model_validator(mode="after")
    def _facts_only_once_each(self) -> Self:
        _require_facts(self.id, self.sentences)
        return self

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        yield from self.sentences


class LadderMaterial(ContractModel):
    material_id: uuid.UUID
    name: str = Field(min_length=1, max_length=300)
    kind: MaterialKind
    role: MaterialRole
    citations: list[Citation] = Field(min_length=1)


class LadderCondition(ContractModel):
    label: str = Field(min_length=1, max_length=120)
    stated: str = Field(min_length=1, max_length=200)
    citations: list[Citation] = Field(min_length=1)

    @model_validator(mode="after")
    def _stated_as_its_source_says(self) -> Self:
        if not any(c.quote and quote_occurs(self.stated, c.quote) for c in self.citations):
            raise ValueError(f"condition {self.label!r} states {self.stated!r}, which no cited quote says")
        return self


class LadderStage(ContractModel):
    stage_id: uuid.UUID
    ordinal: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=300)
    stage_type: StageType
    level: ShownLevel
    sentences: list[ExplainerSentence] = Field(min_length=1)
    materials: list[LadderMaterial]
    conditions: list[LadderCondition]
    reaction_ids: list[uuid.UUID]

    @model_validator(mode="after")
    def _level_follows_the_stage_sentences(self) -> Self:
        _require_facts(f"stage {self.stage_id}", self.sentences)
        expected = weakest_level(sentence.level for sentence in self.sentences)
        if self.level != expected:
            raise ValueError(f"stage {self.stage_id} is {expected}, not {self.level}")
        if len(set(self.reaction_ids)) != len(self.reaction_ids):
            raise ValueError(f"stage {self.stage_id} links each reaction once")
        return self

    def citations(self) -> Iterator[Citation]:
        for sentence in self.sentences:
            yield from sentence.citations
        for material in self.materials:
            yield from material.citations
        for condition in self.conditions:
            yield from condition.citations


class ProcessLadderBlock(BlockBase):
    kind: Literal["process_ladder"]
    version: Literal[1]
    craft: CraftRef
    process_id: uuid.UUID
    stages: list[LadderStage] = Field(min_length=1)

    @model_validator(mode="after")
    def _stages_climb_in_order(self) -> Self:
        ordinals = [stage.ordinal for stage in self.stages]
        if any(a >= b for a, b in pairwise(ordinals)):
            raise ValueError(f"ladder {self.id} lists its stages by rising ordinal")
        return self

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for stage in self.stages:
            yield from stage.sentences

    def citations(self) -> Iterator[Citation]:
        for stage in self.stages:
            yield from stage.citations()


class ImageItem(ContractModel):
    media: MediaRef
    claim_ids: list[uuid.UUID] = Field(min_length=1)
    relevance: ImageRelevance

    @model_validator(mode="after")
    def _claims_once_each(self) -> Self:
        if len(set(self.claim_ids)) != len(self.claim_ids):
            raise ValueError(f"image {self.media.id} names each claim it illustrates once")
        return self


class ImagesBlock(BlockBase):
    kind: Literal["images"]
    version: Literal[1]
    items: list[ImageItem] = Field(min_length=1, max_length=IMAGES_MAX)

    @model_validator(mode="after")
    def _each_image_once(self) -> Self:
        ids = [item.media.id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError(f"images {self.id} shows each image once")
        return self

    def illustrated_claim_ids(self) -> set[str]:
        return {str(claim_id) for item in self.items for claim_id in item.claim_ids}


def _require_facts(owner: str, sentences: list[ExplainerSentence]) -> None:
    ids = [sentence.id for sentence in sentences]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{owner} lists each sentence once")
    if any(sentence.level not in FACT_LEVELS for sentence in sentences):
        raise ValueError(f"{owner} states facts only; a hypothesis is an open question")


def payload_sentences(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if payload["kind"] == LADDER_KIND:
        return [sentence for stage in payload["stages"] for sentence in stage["sentences"]]
    return list(payload.get("sentences", ()))


def with_payload_sentences(payload: Mapping[str, Any], change: SentenceChange) -> dict[str, Any]:
    if payload["kind"] == LADDER_KIND:
        stages = [
            {**stage, "sentences": [change(sentence) for sentence in stage["sentences"]]}
            for stage in payload["stages"]
        ]
        return {**payload, "stages": stages}
    if "sentences" in payload:
        return {**payload, "sentences": [change(sentence) for sentence in payload["sentences"]]}
    return dict(payload)
