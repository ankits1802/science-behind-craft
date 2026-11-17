from __future__ import annotations

import uuid
from collections.abc import Iterator, Mapping
from types import MappingProxyType
from typing import Annotated, Any, Literal, Self

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator

from .base import ContractModel, HttpsUrl, absent
from .blocks import (
    BlockBase,
    ImagesBlock,
    ProcessLadderBlock,
    ProseBlock,
    SentenceChange,
    sentences_in_payload,
    with_sentences_in_payload,
)
from .blocks_matter import (
    MaterialCardBlock,
    Molecule3dBlock,
    ReactionPlayerBlock,
    SimulationBlock,
    WhatIfBlock,
    ZoomStoryBlock,
)
from .blocks_people import (
    ArtisanVoiceBlock,
    CompareBlock,
    DesignsBlock,
    ExpertViewBlock,
    InPracticeBlock,
    OpenQuestionsBlock,
    QuizBlock,
    expert_pairing_problems,
)
from .blocks_place import MapLayerBlock, RegionStoryBlock, SeasonsBlock, SupplyMapBlock, TimelineMapBlock
from .citations import SourceRef
from .composition import FOLLOW_UPS_MAX, HEADING_MAX_CHARS
from .crafts import MAX_CANDIDATES, QUESTION_MAX_CHARS, CraftRef
from .evidence import EVIDENCE_ID_MAX_CHARS
from .vocabulary import AnswerLanguage, Depth, Discipline

__all__ = [
    "BLOCK_MODELS",
    "BLOCK_PHASES",
    "BUILT_BLOCK_KINDS",
    "EXPLAINER_EVENTS",
    "EXPLAINER_SCHEMA_VERSION",
    "FINAL_SECTION_STATES",
    "PIECE_PREFIX",
    "SEARCHED_MAX_CHARS",
    "SECTION_ID_PATTERN",
    "SECTION_STATES",
    "STORED_SOURCE_PREFIX",
    "STORED_TRAIL_PREFIXES",
    "TRAIL_GROUPS",
    "TRAIL_GROUP_OF_SOURCE",
    "TRAIL_KEY_PATTERN",
    "TRAIL_PUBLISHER_MAX_CHARS",
    "TRAIL_STAGES",
    "TRAIL_TITLE_MAX_CHARS",
    "WORKING_SECTION_STATES",
    "Block",
    "BlockEvent",
    "Explainer",
    "ExplainerSection",
    "SectionDoneEvent",
    "SectionStartedEvent",
    "SectionStateEvent",
    "TrailEvent",
    "Understood",
    "explainer_blocks",
    "payload_sentences",
    "with_payload_sentences",
]

EXPLAINER_SCHEMA_VERSION = 1
SECTION_ID_PATTERN = r"^s[1-9]\d{0,2}$"
SEARCHED_MAX_CHARS = 2000
WORKING_SECTION_STATES = ("RESEARCHING", "WRITING", "CHECKING")
FINAL_SECTION_STATES = ("READY", "EMPTY")
SECTION_STATES = (*WORKING_SECTION_STATES, *FINAL_SECTION_STATES)
TRAIL_STAGES = ("FOUND", "READ", "QUOTED")
TRAIL_GROUPS = ("PAPERS", "ENCYCLOPAEDIA", "DATASETS", "WEB", "STORED")
TRAIL_KEY_PATTERN = r"^[a-z][a-z0-9_]{1,39}:\S+$"
STORED_SOURCE_PREFIX = "source"
PIECE_PREFIX = "piece"
STORED_TRAIL_PREFIXES = (STORED_SOURCE_PREFIX, PIECE_PREFIX)
TRAIL_TITLE_MAX_CHARS = 1000
TRAIL_PUBLISHER_MAX_CHARS = 300
TRAIL_GROUP_OF_SOURCE: Mapping[str, str] = MappingProxyType(
    {
        "PAPER": "PAPERS",
        "BOOK": "PAPERS",
        "BOOK_CHAPTER": "PAPERS",
        "GI_JOURNAL": "PAPERS",
        "GOVERNMENT_REPORT": "PAPERS",
        "FIELD_TESTIMONY": "PAPERS",
        "ENCYCLOPEDIA": "ENCYCLOPAEDIA",
        "DATASET": "DATASETS",
        "COMPOUND_RECORD": "DATASETS",
        "WEB_PAGE": "WEB",
        "OTHER": "WEB",
    }
)

WorkingState = Literal[*WORKING_SECTION_STATES]
FinalState = Literal[*FINAL_SECTION_STATES]
TrailStage = Literal[*TRAIL_STAGES]
TrailGroup = Literal[*TRAIL_GROUPS]
SectionId = Annotated[str, Field(pattern=SECTION_ID_PATTERN)]

BLOCK_MODELS: Mapping[str, type[BlockBase]] = MappingProxyType(
    {
        "prose": ProseBlock,
        "process_ladder": ProcessLadderBlock,
        "region_story": RegionStoryBlock,
        "map_layer": MapLayerBlock,
        "reaction_player": ReactionPlayerBlock,
        "material_card": MaterialCardBlock,
        "molecule_3d": Molecule3dBlock,
        "images": ImagesBlock,
        "simulation": SimulationBlock,
        "what_if": WhatIfBlock,
        "timeline_map": TimelineMapBlock,
        "zoom_story": ZoomStoryBlock,
        "expert_view": ExpertViewBlock,
        "seasons": SeasonsBlock,
        "supply_map": SupplyMapBlock,
        "compare": CompareBlock,
        "in_practice": InPracticeBlock,
        "quiz": QuizBlock,
        "open_questions": OpenQuestionsBlock,
        "artisan_voice": ArtisanVoiceBlock,
        "designs": DesignsBlock,
    }
)
BLOCK_PHASES: Mapping[str, str] = MappingProxyType(
    {
        "prose": "A",
        "process_ladder": "A",
        "images": "A",
        "region_story": "B",
        "map_layer": "B",
        "reaction_player": "B",
        "material_card": "B",
        "molecule_3d": "B",
        "expert_view": "B",
        "seasons": "B",
        "supply_map": "B",
        "simulation": "C",
        "what_if": "C",
        "zoom_story": "C",
        "timeline_map": "C",
        "quiz": "D",
        "compare": "D",
        "in_practice": "D",
        "open_questions": "D",
        "artisan_voice": "E",
        "designs": "DEFERRED",
    }
)
BUILT_BLOCK_KINDS = (
    "prose",
    "process_ladder",
    "images",
    "region_story",
    "map_layer",
    "expert_view",
    "seasons",
    "supply_map",
    "reaction_player",
    "material_card",
    "molecule_3d",
)

Block = Annotated[
    ProseBlock
    | ProcessLadderBlock
    | RegionStoryBlock
    | MapLayerBlock
    | ReactionPlayerBlock
    | MaterialCardBlock
    | Molecule3dBlock
    | ImagesBlock
    | SimulationBlock
    | WhatIfBlock
    | TimelineMapBlock
    | ZoomStoryBlock
    | ExpertViewBlock
    | SeasonsBlock
    | SupplyMapBlock
    | CompareBlock
    | InPracticeBlock
    | QuizBlock
    | OpenQuestionsBlock
    | ArtisanVoiceBlock
    | DesignsBlock,
    Field(discriminator="kind"),
]


class Understood(ContractModel):
    crafts: list[CraftRef] = Field(max_length=MAX_CANDIDATES)
    candidates: list[CraftRef] = Field(max_length=MAX_CANDIDATES)
    depth: Depth
    language: AnswerLanguage

    @model_validator(mode="after")
    def _each_craft_once(self) -> Self:
        slugs = [craft.slug for craft in (*self.crafts, *self.candidates)]
        if len(set(slugs)) != len(slugs):
            raise ValueError("a craft is chosen or offered, once")
        return self


class SectionStartedEvent(ContractModel):
    id: SectionId
    discipline: Discipline
    title: str = Field(min_length=1, max_length=HEADING_MAX_CHARS)
    original: str | None = Field(default=None, min_length=1, exclude_if=absent)
    order: int = Field(ge=1)
    state: WorkingState


class SectionStateEvent(ContractModel):
    section_id: SectionId
    state: WorkingState


class BlockEvent(ContractModel):
    section_id: SectionId
    block: Block

    @model_validator(mode="after")
    def _only_blocks_the_reader_can_see(self) -> Self:
        _require_built(self.block)
        return self


class SectionDoneEvent(ContractModel):
    section_id: SectionId
    state: FinalState
    searched: str | None = Field(min_length=1, max_length=SEARCHED_MAX_CHARS)

    @model_validator(mode="after")
    def _an_empty_section_says_what_it_searched(self) -> Self:
        _require_searched(self.section_id, self.state, self.searched)
        return self


class TrailEvent(ContractModel):
    key: str = Field(min_length=3, max_length=EVIDENCE_ID_MAX_CHARS, pattern=TRAIL_KEY_PATTERN)
    stage: TrailStage
    group: TrailGroup
    title: str = Field(min_length=1, max_length=TRAIL_TITLE_MAX_CHARS)
    url: HttpsUrl | None
    publisher: str | None = Field(max_length=TRAIL_PUBLISHER_MAX_CHARS)
    year: int | None
    source_id: str | None
    stored_at: AwareDatetime | None

    @model_validator(mode="after")
    def _stored_knowledge_is_marked_as_such(self) -> Self:
        prefix, _, rest = self.key.partition(":")
        stored = prefix in STORED_TRAIL_PREFIXES
        if stored != (self.group == "STORED"):
            raise ValueError(f"trail {self.key} is STORED exactly when it is a stored source or piece")
        if stored and self.stage == "READ":
            raise ValueError(f"trail {self.key} is stored knowledge, found or quoted, never read again")
        if (prefix == PIECE_PREFIX) != (self.stored_at is not None):
            raise ValueError(
                f"trail {self.key} carries the date of earlier research exactly when it is a piece"
            )
        if prefix == "source" and self.source_id != rest:
            raise ValueError(f"trail {self.key} names its stored source")
        return self


class ExplainerSection(ContractModel):
    id: SectionId
    discipline: Discipline
    title: str = Field(min_length=1, max_length=HEADING_MAX_CHARS)
    original: str | None = Field(default=None, min_length=1, exclude_if=absent)
    order: int = Field(ge=1)
    state: FinalState
    blocks: list[Block]
    searched: str | None = Field(min_length=1, max_length=SEARCHED_MAX_CHARS)

    @model_validator(mode="after")
    def _ready_with_blocks_or_empty_with_a_reason(self) -> Self:
        _require_searched(self.id, self.state, self.searched)
        if (self.state == "READY") != bool(self.blocks):
            raise ValueError(f"section {self.id} is READY exactly when it holds blocks")
        for block in self.blocks:
            _require_built(block)
        cited = set().union(*(block.cited_claim_ids() for block in self.blocks))
        if any(not block.illustrated_claim_ids() <= cited for block in self.blocks):
            raise ValueError(f"section {self.id} shows images only for claims it cites")
        pairing = expert_pairing_problems(self.blocks)
        if pairing:
            raise ValueError(f"section {self.id}: {'; '.join(pairing)}")
        return self


class Explainer(ContractModel):
    schema_version: Literal[1]
    answer_id: uuid.UUID
    question: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    understood: Understood
    sections: list[ExplainerSection] = Field(min_length=1)
    sources: list[SourceRef]
    follow_ups: list[str] = Field(max_length=FOLLOW_UPS_MAX)
    created_at: AwareDatetime

    @model_validator(mode="after")
    def _sections_in_order_and_sources_as_cited(self) -> Self:
        if [section.order for section in self.sections] != list(range(1, len(self.sections) + 1)):
            raise ValueError("sections are listed by order, 1 to n")
        if len({section.id for section in self.sections}) != len(self.sections):
            raise ValueError("each section id is used once")
        block_ids = [block.id for block in explainer_blocks(self)]
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("each block id is used once")
        if all(section.state == "EMPTY" for section in self.sections):
            raise ValueError("an explainer shows at least one ready section")
        ordered = dict.fromkeys(sid for block in explainer_blocks(self) for sid in block.cited_source_ids())
        if [source.id for source in self.sources] != list(ordered):
            raise ValueError("sources lists every cited source once, in order of first citation")
        return self


def explainer_blocks(explainer: Explainer) -> Iterator[BlockBase]:
    for section in explainer.sections:
        yield from section.blocks


def payload_sentences(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return sentences_in_payload(payload, _sentence_spec(payload))


def with_payload_sentences(payload: Mapping[str, Any], change: SentenceChange) -> dict[str, Any]:
    return with_sentences_in_payload(payload, _sentence_spec(payload), change)


def _sentence_spec(payload: Mapping[str, Any]) -> tuple[tuple[str, Any], ...]:
    model = BLOCK_MODELS.get(str(payload.get("kind")))
    return model.SENTENCES if model is not None else ()


def _require_built(block: BlockBase) -> None:
    if block.kind not in BUILT_BLOCK_KINDS:
        raise ValueError(f"block {block.id} is a {block.kind} block, which is not built yet")


def _require_searched(section_id: str, state: str, searched: str | None) -> None:
    if (state == "EMPTY") != (searched is not None):
        raise ValueError(f"section {section_id} says what it searched exactly when it is EMPTY")


EXPLAINER_EVENTS: Mapping[str, TypeAdapter[Any]] = MappingProxyType(
    {
        "understood": TypeAdapter(Understood),
        "section_started": TypeAdapter(SectionStartedEvent),
        "section_state": TypeAdapter(SectionStateEvent),
        "block": TypeAdapter(BlockEvent),
        "section_done": TypeAdapter(SectionDoneEvent),
        "trail": TypeAdapter(TrailEvent),
    }
)
