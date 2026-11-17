from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.research.reactions import ReactionSpecies, mhchem_equation

from .balance import CHECKER_VERSION, ProposedSpecies, balance

__all__ = ["CheckedReaction", "SpeciesProposal", "check_reaction"]


@dataclass(frozen=True)
class SpeciesProposal:
    role: str
    formula: str | None
    name: str | None


@dataclass(frozen=True)
class CheckedReaction:
    balanced: bool
    coefficients: tuple[int, ...] | None
    checker_version: str | None
    equation_input: str | None
    equation_balanced: str | None


def check_reaction(species: Sequence[SpeciesProposal]) -> CheckedReaction:
    proposed = mhchem_equation([_species(s, None) for s in species])
    if proposed is None:
        return CheckedReaction(False, None, None, None, None)
    result = balance([ProposedSpecies(s.role, s.formula or "") for s in species])
    if not result.balanced or result.coefficients is None:
        return CheckedReaction(False, None, None, proposed, None)
    weighted = [_species(s, c) for s, c in zip(species, result.coefficients, strict=True)]
    return CheckedReaction(True, result.coefficients, CHECKER_VERSION, proposed, mhchem_equation(weighted))


def _species(proposal: SpeciesProposal, coefficient: int | None) -> ReactionSpecies:
    return ReactionSpecies(
        role=proposal.role,
        formula=proposal.formula,
        name=proposal.name,
        coefficient=coefficient,
        compound_id=None,
    )
