from __future__ import annotations

import uuid
from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .reactions import SPECIES_ROLES
from .vocabulary import MaterialKind, MaterialRole, ReactionKind, StageType

__all__ = [
    "TIMING_KINDS",
    "PageProcess",
    "PageReaction",
    "PageSpecies",
    "PageStage",
    "StageItem",
    "StageTiming",
]

TIMING_KINDS = ("DURATION", "SEASON")

ClaimIds = list[uuid.UUID]


class StageItem(ContractModel):
    id: uuid.UUID
    name: str = Field(min_length=1)
    kind: MaterialKind
    role: MaterialRole
    local_names: list[str]
    botanical_name: str | None
    pubchem_cid: int | None = Field(ge=1)
    claim_ids: ClaimIds = Field(min_length=1)


class StageTiming(ContractModel):
    kind: Literal[*TIMING_KINDS]
    text: str = Field(min_length=1)
    claim_id: uuid.UUID


class PageSpecies(ContractModel):
    role: Literal[*SPECIES_ROLES]
    name: str | None
    formula: str | None
    coefficient: int | None = Field(ge=1)


class PageReaction(ContractModel):
    id: uuid.UUID | None
    kind: ReactionKind
    label: str = Field(min_length=1)
    species: list[PageSpecies] = Field(min_length=2)
    balanced: bool
    equation: str | None
    claim_ids: ClaimIds = Field(min_length=1)

    @model_validator(mode="after")
    def _equation_only_when_balanced(self) -> Self:
        if (self.equation is not None) != self.balanced:
            raise ValueError("a reaction shows an equation only when it balances")
        return self


class PageStage(ContractModel):
    id: uuid.UUID
    order: int | None = Field(ge=1)
    name: str = Field(min_length=1)
    local_name: str | None
    stage_type: StageType
    claim_ids: ClaimIds = Field(min_length=1)
    materials: list[StageItem]
    tools: list[StageItem]
    timing: list[StageTiming]
    reactions: list[PageReaction]
    differ: list[str]

    def own_claim_ids(self) -> list[uuid.UUID]:
        return [*self.claim_ids, *(timing.claim_id for timing in self.timing)]

    def cited_claim_ids(self) -> list[uuid.UUID]:
        items = [claim_id for item in [*self.materials, *self.tools] for claim_id in item.claim_ids]
        reactions = [claim_id for reaction in self.reactions for claim_id in reaction.claim_ids]
        return [*self.own_claim_ids(), *items, *reactions]


class PageProcess(ContractModel):
    process_id: uuid.UUID | None
    stages: list[PageStage]
    reactions: list[PageReaction]

    def cited_claim_ids(self) -> list[uuid.UUID]:
        staged = [claim_id for stage in self.stages for claim_id in stage.cited_claim_ids()]
        return [*staged, *(claim_id for reaction in self.reactions for claim_id in reaction.claim_ids)]
