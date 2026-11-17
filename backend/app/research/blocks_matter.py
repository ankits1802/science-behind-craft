from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import ClassVar, Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .blocks import SENTENCE, BlockBase, ExplainerSentence, SentenceSpec, require_facts
from .citations import Citation
from .reactions import SPECIES_ROLES, ReactionSpecies, mhchem_equation, reaction_level
from .subject_keys import TermKey
from .terms import WIKIDATA_ID_PATTERN
from .vocabulary import MaterialKind, MaterialRole, ReactionKind, ShownLevel

__all__ = [
    "MaterialCardBlock",
    "Molecule3dBlock",
    "ReactionPlayerBlock",
    "ReactionStep",
]


class ReactionStep(ContractModel):
    reaction_id: uuid.UUID
    stage_id: uuid.UUID | None
    kind: ReactionKind
    label: str = Field(min_length=1, max_length=200)
    species: list[ReactionSpecies] = Field(min_length=2)
    equation: str | None
    balanced: bool
    level: ShownLevel
    citations: list[Citation] = Field(min_length=1)

    @model_validator(mode="after")
    def _the_science_engine_s_reaction(self) -> Self:
        if {species.role for species in self.species} != set(SPECIES_ROLES):
            raise ValueError(f"reaction {self.reaction_id} names at least one reactant and one product")
        if self.equation != mhchem_equation(self.species):
            raise ValueError(f"reaction {self.reaction_id} equation is not built from its species")
        if self.balanced and self.equation is None:
            raise ValueError(f"reaction {self.reaction_id} is balanced only with a formula for every species")
        level, _ = reaction_level(
            [c.level for c in self.citations], balanced=self.balanced, species=self.species
        )
        if self.level != level:
            raise ValueError(f"reaction {self.reaction_id} is {level}, not {self.level}")
        return self


class ReactionPlayerBlock(BlockBase):
    kind: Literal["reaction_player"]
    version: Literal[1]
    steps: list[ReactionStep] = Field(min_length=1)

    @model_validator(mode="after")
    def _each_reaction_once(self) -> Self:
        ids = [step.reaction_id for step in self.steps]
        if len(set(ids)) != len(ids):
            raise ValueError(f"reaction player {self.id} plays each reaction once")
        return self

    def citations(self) -> Iterator[Citation]:
        for step in self.steps:
            yield from step.citations

    def shown_labels(self) -> list[str]:
        return [step.label for step in self.steps]


class MaterialCardBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (("facts", [SENTENCE]), ("handling", [SENTENCE]))

    kind: Literal["material_card"]
    version: Literal[1]
    material_id: uuid.UUID | None
    compound_id: uuid.UUID | None
    term_key: TermKey | None
    name: str = Field(min_length=1, max_length=300)
    material_kind: MaterialKind | None
    role: MaterialRole | None
    formula: str | None = Field(min_length=1, max_length=120)
    pubchem_cid: int | None = Field(ge=1)
    wikidata_id: str | None = Field(pattern=WIKIDATA_ID_PATTERN)
    local_names: list[str]
    facts: list[ExplainerSentence] = Field(min_length=1)
    handling: list[ExplainerSentence]

    @model_validator(mode="after")
    def _values_from_stored_rows(self) -> Self:
        require_facts(f"material card {self.id}", [*self.facts, *self.handling])
        if (self.material_kind or self.role) and self.material_id is None:
            raise ValueError(f"material card {self.id} shows a kind or role only from its stored material")
        if (self.formula or self.pubchem_cid) and self.compound_id is None:
            raise ValueError(f"material card {self.id} shows a formula or PubChem id only from its compound")
        if (self.local_names or self.wikidata_id) and self.term_key is None:
            raise ValueError(
                f"material card {self.id} shows local names or Wikidata only from its glossary term"
            )
        folded = [name.casefold() for name in self.local_names]
        if len(set(folded)) != len(folded) or any(not name.strip() for name in self.local_names):
            raise ValueError(f"material card {self.id} lists each local name once")
        return self

    def shown_labels(self) -> list[str]:
        return [self.name, *self.local_names]


class Molecule3dBlock(BlockBase):
    kind: Literal["molecule_3d"]
    version: Literal[1]
    compound_id: uuid.UUID
    pubchem_cid: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=300)
    formula: str | None = Field(min_length=1, max_length=120)
    source_id: str = Field(min_length=1)

    def direct_source_ids(self) -> Iterator[str]:
        yield self.source_id

    def shown_labels(self) -> list[str]:
        return [self.name]
