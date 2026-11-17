from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from typing import Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel
from .vocabulary import weakest_level

__all__ = [
    "SPECIES_ROLES",
    "UNBALANCED_LEVEL_CAP",
    "UNBALANCED_REASON",
    "ReactionSpecies",
    "mhchem_equation",
    "reaction_level",
]

SPECIES_ROLES = ("REACTANT", "PRODUCT")
UNBALANCED_REASON = "unbalanced"
UNBALANCED_LEVEL_CAP = "HYPOTHESIS"

SpeciesRole = Literal[*SPECIES_ROLES]


class ReactionSpecies(ContractModel):
    role: SpeciesRole
    formula: str | None = Field(max_length=120)
    name: str | None = Field(max_length=300)
    coefficient: int | None = Field(ge=1)
    compound_id: uuid.UUID | None

    @model_validator(mode="after")
    def _named_or_formulated(self) -> Self:
        if not (self.formula or self.name):
            raise ValueError("a species has a formula, a name or both")
        return self


def mhchem_equation(species: Sequence[ReactionSpecies]) -> str | None:
    if any(not s.formula for s in species):
        return None
    sides = [" + ".join(_term(s) for s in species if s.role == role) for role in SPECIES_ROLES]
    return " -> ".join(sides)


def reaction_level(
    levels: Iterable[str], *, balanced: bool, species: Sequence[ReactionSpecies]
) -> tuple[str, str | None]:
    level = weakest_level(levels)
    if balanced or mhchem_equation(species) is None:
        return level, None
    return weakest_level((level, UNBALANCED_LEVEL_CAP)), UNBALANCED_REASON


def _term(species: ReactionSpecies) -> str:
    coefficient = species.coefficient
    return f"{coefficient} {species.formula}" if coefficient and coefficient > 1 else str(species.formula)
