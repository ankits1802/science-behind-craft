from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.core.errors import InvalidInput
from app.data.craft_text import fold
from app.research.blocks_matter import ReactionStep
from app.research.reactions import ReactionSpecies, mhchem_equation, reaction_level
from app.science.balance import ProposedSpecies, balance
from app.science.records import CompoundRecord

__all__ = ["COMPOUND_RECORD_BASIS", "inferred_step", "named_compounds"]

COMPOUND_RECORD_BASIS = "COMPOUND_RECORD"


def named_compounds(
    compounds: Sequence[CompoundRecord], names: Mapping[str, CompoundRecord]
) -> dict[str, CompoundRecord]:
    found = {fold(compound.name): compound for compound in compounds if compound.formula}
    found.update({fold(name): compound for name, compound in names.items() if compound.formula})
    return {key: compound for key, compound in found.items() if key}


def inferred_step(step: ReactionStep, named: Mapping[str, CompoundRecord]) -> ReactionStep:
    if step.balanced:
        return step
    records = [named.get(fold(species.name or "")) for species in step.species]
    if any(record is None or record.source_id is None for record in records):
        return step
    resolved = [record for record in records if record is not None]
    proposed = [ProposedSpecies(s.role, str(r.formula)) for s, r in zip(step.species, resolved, strict=True)]
    try:
        found = balance(proposed)
    except InvalidInput:
        return step
    if not found.balanced or found.coefficients is None:
        return step
    species = [
        ReactionSpecies(role=s.role, formula=r.formula, name=s.name, coefficient=n, compound_id=r.id)
        for s, r, n in zip(step.species, resolved, found.coefficients, strict=True)
    ]
    level, _ = reaction_level([c.level for c in step.citations], balanced=True, species=species)
    return ReactionStep.model_validate(
        {
            **step.model_dump(by_alias=True),
            "species": [item.model_dump(by_alias=True) for item in species],
            "equation": mhchem_equation(species),
            "balanced": True,
            "level": level,
            "formulaBasis": COMPOUND_RECORD_BASIS,
            "formulaSources": list(dict.fromkeys(str(r.source_id) for r in resolved)),
        }
    )
