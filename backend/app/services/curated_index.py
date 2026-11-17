from __future__ import annotations

import uuid
from typing import Literal

from pydantic import AwareDatetime, Field

from app.models.enums import COVERAGE_CLASSES, PLACE_ROLES
from app.research.base import ContractModel
from app.research.vocabulary import Discipline, MaterialKind, MaterialRole, ReactionKind

__all__ = [
    "CURATED_PAGE_SCHEMA_VERSION",
    "CuratedPage",
    "IndexCommunity",
    "IndexConflict",
    "IndexEnvironment",
    "IndexFact",
    "IndexMaterial",
    "IndexOverview",
    "IndexPicture",
    "IndexPlace",
    "IndexQuestion",
    "IndexReaction",
    "IndexSearch",
    "IndexSection",
    "IndexSpecies",
    "IndexStage",
    "IndexTerm",
    "IndexTiming",
    "IndexTool",
]

CURATED_PAGE_SCHEMA_VERSION = 1

ClaimIds = list[uuid.UUID]


class IndexSearch(ContractModel):
    query: str
    site: str


class IndexTiming(ContractModel):
    text: str
    claim_id: uuid.UUID


class IndexPlace(ContractModel):
    key: str
    name: str
    kind: str
    role: Literal[*PLACE_ROLES]
    district: str | None
    district_lgd: int | None
    state: str | None
    state_lgd: int | None
    country: str
    wikidata_id: str | None
    location_id: uuid.UUID | None
    concept_id: uuid.UUID
    claim_ids: ClaimIds


class IndexCommunity(ContractModel):
    key: str
    kind: str
    name: str
    local_names: list[str]
    honours: list[str]
    place_key: str | None
    concept_id: uuid.UUID
    claim_ids: ClaimIds


class IndexStage(ContractModel):
    key: str
    stage_id: uuid.UUID
    concept_id: uuid.UUID
    local_name: str | None
    order: int | None
    order_claim_id: uuid.UUID | None
    duration: IndexTiming | None
    season: IndexTiming | None
    claim_ids: ClaimIds


class IndexMaterial(ContractModel):
    key: str
    material_id: uuid.UUID
    concept_id: uuid.UUID
    name: str
    kind: MaterialKind
    role: MaterialRole
    local_names: list[str]
    botanical_name: str | None
    pubchem_cid: int | None
    claim_ids: ClaimIds


class IndexTool(ContractModel):
    key: str
    material_id: uuid.UUID
    concept_id: uuid.UUID
    name: str
    local_names: list[str]
    claim_ids: ClaimIds


class IndexSpecies(ContractModel):
    name: str
    formula: str | None


class IndexReaction(ContractModel):
    key: str
    reaction_id: uuid.UUID | None
    stage_key: str | None
    kind: ReactionKind
    reactants: list[IndexSpecies]
    products: list[IndexSpecies]
    claim_ids: ClaimIds


class IndexTerm(ContractModel):
    key: str
    term_key: str | None
    term: str
    names: list[str]
    meaning: str
    language: str | None
    script: str | None
    concept_id: uuid.UUID
    claim_ids: ClaimIds


class IndexPicture(ContractModel):
    key: str
    media_ref_id: uuid.UUID
    caption: str
    stage_key: str | None
    claim_ids: ClaimIds


class IndexEnvironment(ContractModel):
    factor: str
    place_key: str | None
    claim_ids: ClaimIds


class IndexFact(ContractModel):
    label: str
    value: str
    claim_ids: ClaimIds


class IndexConflict(ContractModel):
    about: str
    claim_ids: ClaimIds


class IndexQuestion(ContractModel):
    key: str
    question: str
    settled_by: str | None
    claim_ids: ClaimIds


class IndexSection(ContractModel):
    discipline: Discipline
    piece_id: uuid.UUID


class IndexOverview(ContractModel):
    lede_piece_id: uuid.UUID | None = None
    sections: list[IndexSection] = Field(default_factory=list)
    key_facts: list[IndexFact] = Field(default_factory=list)


class CuratedPage(ContractModel):
    schema_version: Literal[1] = CURATED_PAGE_SCHEMA_VERSION
    craft_slug: str
    version: int = Field(ge=1)
    curated_at: AwareDatetime
    coverage: Literal[*COVERAGE_CLASSES]
    searched: list[IndexSearch]
    process_id: uuid.UUID | None
    craft_concepts: dict[str, uuid.UUID]
    overview: IndexOverview
    conflicts: list[IndexConflict]
    open_questions: list[IndexQuestion]
    places: list[IndexPlace]
    communities: list[IndexCommunity]
    stages: list[IndexStage]
    materials: list[IndexMaterial]
    tools: list[IndexTool]
    reactions: list[IndexReaction]
    glossary: list[IndexTerm]
    pictures: list[IndexPicture]
    environment: list[IndexEnvironment]

    def concept_kinds(self) -> dict[uuid.UUID, str]:
        kinds = dict.fromkeys(self.craft_concepts.values(), "CRAFT")
        for kind, entries in (
            ("PLACE", self.places),
            ("COMMUNITY", self.communities),
            ("STAGE", self.stages),
            ("MATERIAL", self.materials),
            ("TOOL", self.tools),
            ("TERM", self.glossary),
        ):
            kinds.update((entry.concept_id, kind) for entry in entries)
        return kinds

    def location_ids(self) -> set[uuid.UUID]:
        return {place.location_id for place in self.places if place.location_id is not None}

    def piece_ids(self) -> dict[str, uuid.UUID]:
        parts = {section.discipline: section.piece_id for section in self.overview.sections}
        if self.overview.lede_piece_id is not None:
            parts["lede"] = self.overview.lede_piece_id
        return parts
