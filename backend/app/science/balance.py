from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from sympy import Matrix, Rational

from app.core.errors import InvalidInput
from app.research.reactions import SPECIES_ROLES

from .formula import Formula, parse_formula

__all__ = [
    "BALANCE_OUTCOMES",
    "CHECKER_VERSION",
    "Balance",
    "ProposedSpecies",
    "balance",
    "composition_matrix",
]

CHECKER_VERSION = "balance/v1"
BALANCE_OUTCOMES = ("BALANCED", "NO_SOLUTION", "NOT_UNIQUE", "NOT_POSITIVE")


@dataclass(frozen=True)
class ProposedSpecies:
    role: str
    formula: str


@dataclass(frozen=True)
class Balance:
    outcome: str
    coefficients: tuple[int, ...] | None

    @property
    def balanced(self) -> bool:
        return self.outcome == "BALANCED"


def balance(species: Sequence[ProposedSpecies]) -> Balance:
    roles = [item.role for item in species]
    if set(roles) != set(SPECIES_ROLES):
        raise InvalidInput("a reaction names at least one REACTANT and one PRODUCT and no other role")
    formulas = [parse_formula(item.formula) for item in species]
    basis = Matrix(composition_matrix(roles, formulas)).nullspace()
    if not basis:
        return Balance("NO_SOLUTION", None)
    if len(basis) > 1:
        return Balance("NOT_UNIQUE", None)
    coefficients = _smallest_integers(basis[0])
    if any(value <= 0 for value in coefficients):
        return Balance("NOT_POSITIVE", None)
    return Balance("BALANCED", coefficients)


def composition_matrix(roles: Sequence[str], formulas: Sequence[Formula]) -> list[list[int]]:
    signs = [1 if role == "REACTANT" else -1 for role in roles]
    elements = sorted({symbol for formula in formulas for symbol in formula.counts})
    rows = [
        [sign * formula.counts.get(symbol, 0) for sign, formula in zip(signs, formulas, strict=True)]
        for symbol in elements
    ]
    if any(formula.charge for formula in formulas):
        rows.append([sign * formula.charge for sign, formula in zip(signs, formulas, strict=True)])
    return rows


def _smallest_integers(vector: Matrix) -> tuple[int, ...]:
    rationals = [Rational(value) for value in vector]
    scale = math.lcm(*(int(value.q) for value in rationals))
    integers = [int(value * scale) for value in rationals]
    divisor = math.gcd(*integers)
    integers = [value // divisor for value in integers]
    if all(value <= 0 for value in integers):
        integers = [-value for value in integers]
    return tuple(integers)
