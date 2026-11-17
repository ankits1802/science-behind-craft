from __future__ import annotations

import math
import uuid
from collections.abc import Iterable, Iterator, Sequence
from itertools import combinations, pairwise
from types import MappingProxyType
from typing import Literal, Self

from pydantic import Field, model_validator

from app.research.base import ContractModel
from app.research.citations import Citation, SourceRef, cited_source_ids
from app.research.crafts import CraftRef
from app.research.vocabulary import (
    EvidenceLevel,
    MaterialKind,
    MaterialRole,
    ReactionKind,
    ShownLevel,
    StageType,
    weakest_level,
)

__all__ = [
    "CONDITION_QUANTITIES",
    "CONDITION_UNITS",
    "ENVELOPE_STATUSES",
    "SCIENCE_SCHEMA_VERSION",
    "SOURCES_DIFFER_CELSIUS",
    "SOURCES_DIFFER_RELATIVE",
    "SPECIES_ROLES",
    "UNAVAILABLE_LEVEL",
    "UNBALANCED_LEVEL_CAP",
    "UNBALANCED_REASON",
    "CitedClaim",
    "CompoundRef",
    "ConditionReading",
    "CraftProcess",
    "DeltaH",
    "EnvelopeCheck",
    "ProcessStageView",
    "ProcessView",
    "ReactionSpecies",
    "ReactionView",
    "StageCondition",
    "StageMaterialView",
    "envelope_status",
    "mhchem_equation",
    "process_claims",
    "reaction_level",
    "sources_differ",
]

SCIENCE_SCHEMA_VERSION = 1
CONDITION_QUANTITIES = ("TEMPERATURE", "PH", "DURATION", "CONCENTRATION", "PRESSURE")
CONDITION_UNITS = MappingProxyType(
    {"TEMPERATURE": "°C", "PH": "pH", "DURATION": "h", "CONCENTRATION": "g/L", "PRESSURE": "kPa"}
)
ENVELOPE_STATUSES = ("WITHIN", "OUTSIDE", "NONE")
SPECIES_ROLES = ("REACTANT", "PRODUCT")
SOURCES_DIFFER_RELATIVE = 0.15
SOURCES_DIFFER_CELSIUS = 25.0
UNBALANCED_REASON = "unbalanced"
UNBALANCED_LEVEL_CAP = "HYPOTHESIS"
UNAVAILABLE_LEVEL = "UNAVAILABLE"

ConditionQuantity = Literal[*CONDITION_QUANTITIES]
EnvelopeStatus = Literal[*ENVELOPE_STATUSES]
SpeciesRole = Literal[*SPECIES_ROLES]


class CitedClaim(ContractModel):
    id: uuid.UUID
    text: str = Field(min_length=1)
    level: EvidenceLevel
    citations: list[Citation] = Field(min_length=1)

    @model_validator(mode="after")
    def _citations_belong_to_the_claim(self) -> Self:
        for citation in self.citations:
            if citation.claim_id != str(self.id) or citation.level != self.level:
                raise ValueError(f"citation {citation.id} does not carry claim {self.id} at its level")
        return self


class CompoundRef(ContractModel):
    id: uuid.UUID
    name: str = Field(min_length=1)
    formula: str | None
    pubchem_cid: int | None = Field(ge=1)


class StageMaterialView(ContractModel):
    id: uuid.UUID
    name: str = Field(min_length=1)
    kind: MaterialKind
    role: MaterialRole
    quantity_text: str | None
    compound: CompoundRef | None
    level: EvidenceLevel
    claims: list[CitedClaim] = Field(min_length=1)

    @model_validator(mode="after")
    def _level_is_the_weakest_claim(self) -> Self:
        _require_weakest(self.level, self.claims, f"material {self.id}")
        return self


class EnvelopeCheck(ContractModel):
    status: EnvelopeStatus
    min: float | None
    max: float | None

    @model_validator(mode="after")
    def _bounds_match_the_status(self) -> Self:
        has_bounds = self.min is not None or self.max is not None
        if (self.status == "NONE") == has_bounds:
            raise ValueError("an envelope has bounds exactly when its status is WITHIN or OUTSIDE")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("an envelope's min is at most its max")
        return self


class ConditionReading(ContractModel):
    claim_id: uuid.UUID
    min: float | None
    max: float | None
    stated: str = Field(min_length=1, max_length=200)
    envelope: EnvelopeCheck

    @model_validator(mode="after")
    def _a_bounded_reading_inside_or_outside_its_envelope(self) -> Self:
        if self.min is None and self.max is None:
            raise ValueError("a reading has a min, a max or both")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("a reading's min is at most its max")
        expected = envelope_status(self.min, self.max, self.envelope.min, self.envelope.max)
        if self.envelope.status != expected:
            raise ValueError(f"reading of claim {self.claim_id} is {expected}, not {self.envelope.status}")
        return self


class StageCondition(ContractModel):
    id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=120)
    quantity: ConditionQuantity
    unit: str
    readings: list[ConditionReading] = Field(min_length=1)
    sources_differ: bool
    level: EvidenceLevel
    claims: list[CitedClaim] = Field(min_length=1)

    @model_validator(mode="after")
    def _readings_rest_on_cited_claims(self) -> Self:
        if self.unit != CONDITION_UNITS[self.quantity]:
            raise ValueError(f"{self.quantity} is given in {CONDITION_UNITS[self.quantity]}")
        cited = {claim.id for claim in self.claims}
        if any(reading.claim_id not in cited for reading in self.readings):
            raise ValueError(f"condition {self.id} has a reading whose claim is not listed")
        if self.sources_differ != sources_differ(self.quantity, self.readings):
            raise ValueError(f"condition {self.id} breaks the sources-differ rule")
        _require_weakest(self.level, self.claims, f"condition {self.id}")
        return self


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


class DeltaH(ContractModel):
    kj_per_mol: float
    claim_id: uuid.UUID


class ReactionView(ContractModel):
    id: uuid.UUID
    kind: ReactionKind
    label: str = Field(min_length=1, max_length=200)
    species: list[ReactionSpecies] = Field(min_length=2)
    balanced: bool
    equation: str | None
    checker_version: str | None
    conditions: list[StageCondition]
    delta_h: DeltaH | None
    level: EvidenceLevel
    level_reason: str | None
    claims: list[CitedClaim] = Field(min_length=1)

    @model_validator(mode="after")
    def _balance_equation_and_level_agree(self) -> Self:
        roles = {s.role for s in self.species}
        if roles != set(SPECIES_ROLES):
            raise ValueError(f"reaction {self.id} names at least one reactant and one product")
        _check_coefficients(self)
        if self.equation != mhchem_equation(self.species):
            raise ValueError(f"reaction {self.id} equation is not built from its species")
        level, reason = reaction_level(
            [c.level for c in self.claims], balanced=self.balanced, species=self.species
        )
        if (self.level, self.level_reason) != (level, reason):
            raise ValueError(f"reaction {self.id} is {level} ({reason}), not {self.level}")
        if self.delta_h is not None and self.delta_h.claim_id not in {c.id for c in self.claims}:
            raise ValueError(f"reaction {self.id} shows a ΔH no listed claim cites")
        return self


class ProcessStageView(ContractModel):
    id: uuid.UUID
    ordinal: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=300)
    stage_type: StageType
    level: ShownLevel
    claims: list[CitedClaim]
    materials: list[StageMaterialView]
    conditions: list[StageCondition]
    reactions: list[ReactionView]

    @model_validator(mode="after")
    def _level_follows_the_stage_claims(self) -> Self:
        expected = weakest_level(c.level for c in self.claims) if self.claims else UNAVAILABLE_LEVEL
        if self.level != expected:
            raise ValueError(f"stage {self.id} is {expected}, not {self.level}")
        return self


class ProcessView(ContractModel):
    id: uuid.UUID
    name: str = Field(min_length=1, max_length=300)
    variant: str | None
    stages: list[ProcessStageView]

    @model_validator(mode="after")
    def _stages_in_order(self) -> Self:
        ordinals = [stage.ordinal for stage in self.stages]
        if any(a >= b for a, b in pairwise(ordinals)):
            raise ValueError(f"process {self.id} lists its stages by rising ordinal")
        return self


class CraftProcess(ContractModel):
    schema_version: Literal[1]
    craft: CraftRef
    processes: list[ProcessView]
    sources: list[SourceRef]

    @model_validator(mode="after")
    def _sources_are_the_cited_ones_in_order(self) -> Self:
        if [source.id for source in self.sources] != cited_source_ids(process_claims(self)):
            raise ValueError("sources lists every cited source once, in order of first citation")
        return self


def process_claims(process: CraftProcess) -> Iterator[CitedClaim]:
    for view in process.processes:
        for stage in view.stages:
            yield from _stage_claims(stage)


def _stage_claims(stage: ProcessStageView) -> Iterator[CitedClaim]:
    yield from stage.claims
    for material in stage.materials:
        yield from material.claims
    for condition in stage.conditions:
        yield from condition.claims
    for reaction in stage.reactions:
        yield from reaction.claims
        for condition in reaction.conditions:
            yield from condition.claims


def envelope_status(
    low: float | None, high: float | None, envelope_min: float | None, envelope_max: float | None
) -> str:
    if envelope_min is None and envelope_max is None:
        return "NONE"
    bounds = [value for value in (low, high) if value is not None]
    below = envelope_min is not None and any(value < envelope_min for value in bounds)
    above = envelope_max is not None and any(value > envelope_max for value in bounds)
    return "OUTSIDE" if below or above else "WITHIN"


def sources_differ(quantity: str, readings: Sequence[ConditionReading]) -> bool:
    values = [_representative(reading) for reading in readings]
    for first, second in combinations(values, 2):
        gap = abs(first - second)
        if quantity == "TEMPERATURE":
            if gap > SOURCES_DIFFER_CELSIUS:
                return True
            continue
        scale = max(abs(first), abs(second))
        if scale > 0 and gap / scale > SOURCES_DIFFER_RELATIVE:
            return True
    return False


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


def _representative(reading: ConditionReading) -> float:
    bounds = [value for value in (reading.min, reading.max) if value is not None]
    return sum(bounds) / len(bounds)


def _check_coefficients(reaction: ReactionView) -> None:
    coefficients = [s.coefficient for s in reaction.species]
    if not reaction.balanced:
        if any(c is not None for c in coefficients):
            raise ValueError(f"reaction {reaction.id} is not balanced, so it carries no coefficients")
        return
    if any(c is None for c in coefficients) or any(not s.formula for s in reaction.species):
        raise ValueError(f"balanced reaction {reaction.id} has a formula and coefficient for every species")
    if math.gcd(*[c for c in coefficients if c is not None]) != 1:
        raise ValueError(f"balanced reaction {reaction.id} uses the smallest integer coefficients")
    if not reaction.checker_version:
        raise ValueError(f"balanced reaction {reaction.id} names the checker version that balanced it")


def _require_weakest(level: str, claims: Sequence[CitedClaim], what: str) -> None:
    expected = weakest_level(claim.level for claim in claims)
    if level != expected:
        raise ValueError(f"{what} is {expected}, not {level}")
