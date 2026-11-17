from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .base import ContractModel
from .blocks import BlockBase, ExplainerSentence
from .citations import AnswerSentence, Citation
from .media_refs import MediaRef
from .terms import WIKIDATA_ID_PATTERN
from .vocabulary import MaterialRole, ShownLevel

__all__ = [
    "SIMULATION_MAX_BYTES",
    "SIMULATION_VALUE_KEY_PATTERN",
    "ZOOM_LEVELS",
    "MaterialCardBlock",
    "Molecule3dBlock",
    "ReactionPlayerBlock",
    "ReactionStep",
    "SimulationBlock",
    "SimulationValue",
    "WhatIfBlock",
    "WhatIfOption",
    "ZoomLevel",
    "ZoomStoryBlock",
]

SIMULATION_MAX_BYTES = 200 * 1024
SIMULATION_VALUE_KEY_PATTERN = r"^[a-z][a-zA-Z0-9]{0,39}$"
ZOOM_LEVELS = ("DISTRICT", "WORKSHOP", "CLOTH", "FIBRE", "MOLECULE")

ZoomLevelName = Literal[*ZOOM_LEVELS]


class ReactionStep(ContractModel):
    reaction_id: uuid.UUID
    label: str = Field(min_length=1, max_length=200)
    equation: str | None
    balanced: bool
    level: ShownLevel
    citations: list[Citation] = Field(min_length=1)


class ReactionPlayerBlock(BlockBase):
    kind: Literal["reaction_player"]
    version: Literal[1]
    steps: list[ReactionStep] = Field(min_length=1)

    def citations(self) -> Iterator[Citation]:
        for step in self.steps:
            yield from step.citations


class MaterialCardBlock(BlockBase):
    kind: Literal["material_card"]
    version: Literal[1]
    material_id: uuid.UUID | None
    name: str = Field(min_length=1, max_length=300)
    formula: str | None = Field(max_length=120)
    pubchem_cid: int | None = Field(ge=1)
    wikidata_id: str | None = Field(pattern=WIKIDATA_ID_PATTERN)
    local_names: list[str]
    role: MaterialRole | None
    facts: list[ExplainerSentence] = Field(min_length=1)
    handling: list[ExplainerSentence]

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        yield from self.facts
        yield from self.handling


class Molecule3dBlock(BlockBase):
    kind: Literal["molecule_3d"]
    version: Literal[1]
    pubchem_cid: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=300)
    formula: str | None = Field(max_length=120)
    source_id: str = Field(min_length=1)

    def direct_source_ids(self) -> Iterator[str]:
        yield self.source_id


class ZoomLevel(ContractModel):
    level: ZoomLevelName
    media: MediaRef | None
    district_lgd: int | None = Field(ge=1)
    pubchem_cid: int | None = Field(ge=1)
    sentence: ExplainerSentence

    @model_validator(mode="after")
    def _each_level_shows_real_matter(self) -> Self:
        shown = {
            "DISTRICT": self.district_lgd is not None,
            "MOLECULE": self.pubchem_cid is not None,
        }.get(self.level, self.media is not None)
        if not shown:
            raise ValueError(f"zoom level {self.level} is shown only with its district, image or compound")
        return self


class ZoomStoryBlock(BlockBase):
    kind: Literal["zoom_story"]
    version: Literal[1]
    levels: list[ZoomLevel] = Field(min_length=2)

    @model_validator(mode="after")
    def _levels_zoom_in_once_each(self) -> Self:
        ranks = [ZOOM_LEVELS.index(level.level) for level in self.levels]
        if ranks != sorted(set(ranks)):
            raise ValueError(f"zoom story {self.id} zooms in level by level, each level once")
        return self

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for level in self.levels:
            yield level.sentence


class SimulationValue(ContractModel):
    key: str = Field(pattern=SIMULATION_VALUE_KEY_PATTERN)
    value: float
    unit: str | None = Field(max_length=40)
    citations: list[Citation] = Field(min_length=1)


class SimulationBlock(BlockBase):
    kind: Literal["simulation"]
    version: Literal[1]
    concept: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=120)
    created_at: AwareDatetime
    html: str = Field(min_length=1)
    html_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    values: list[SimulationValue] = Field(min_length=1)
    hidden: bool

    @model_validator(mode="after")
    def _small_and_fed_only_cited_values(self) -> Self:
        if len(self.html.encode("utf-8")) > SIMULATION_MAX_BYTES:
            raise ValueError(f"simulation {self.id} is larger than {SIMULATION_MAX_BYTES} bytes")
        keys = [value.key for value in self.values]
        if len(set(keys)) != len(keys):
            raise ValueError(f"simulation {self.id} passes each value once")
        return self

    def citations(self) -> Iterator[Citation]:
        for value in self.values:
            yield from value.citations


class WhatIfOption(ContractModel):
    label: str = Field(min_length=1, max_length=200)
    outcome: ExplainerSentence | None


class WhatIfBlock(BlockBase):
    kind: Literal["what_if"]
    version: Literal[1]
    changed: str = Field(min_length=1, max_length=200)
    options: list[WhatIfOption] = Field(min_length=2)

    def cited_sentences(self) -> Iterator[AnswerSentence]:
        for option in self.options:
            if option.outcome is not None:
                yield option.outcome
