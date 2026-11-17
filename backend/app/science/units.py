from __future__ import annotations

import math
from dataclasses import dataclass

from pint.errors import PintError

from app.core.errors import InvalidInput
from app.research.unit_registry import unit_registry
from app.schemas.science import CONDITION_QUANTITIES, CONDITION_UNITS

__all__ = ["NORMALISED_DIGITS", "PH_UNIT", "Bounds", "normalised_bounds"]

NORMALISED_DIGITS = 6
PH_UNIT = CONDITION_UNITS["PH"]


@dataclass(frozen=True)
class Bounds:
    low: float | None
    high: float | None


def normalised_bounds(quantity: str, stated: Bounds, unit: str) -> Bounds:
    if quantity not in CONDITION_QUANTITIES:
        raise InvalidInput(f"{quantity!r} is not one of {', '.join(CONDITION_QUANTITIES)}")
    _check_bounds(stated, unit)
    if quantity == "PH":
        if unit != PH_UNIT:
            raise InvalidInput(f"a pH is stated in {PH_UNIT!r}, not {unit!r}")
        return Bounds(_rounded(stated.low), _rounded(stated.high))
    target = CONDITION_UNITS[quantity]
    return Bounds(_converted(stated.low, unit, target), _converted(stated.high, unit, target))


def _check_bounds(stated: Bounds, unit: str) -> None:
    given = [value for value in (stated.low, stated.high) if value is not None]
    if not given:
        raise InvalidInput(f"a reading in {unit!r} has a lower bound, an upper bound or both")
    if any(not math.isfinite(value) for value in given):
        raise InvalidInput(f"a reading in {unit!r} has finite bounds")
    if stated.low is not None and stated.high is not None and stated.low > stated.high:
        raise InvalidInput(f"a reading's lower bound {stated.low} is above its upper bound {stated.high}")


def _converted(value: float | None, unit: str, target: str) -> float | None:
    if value is None:
        return None
    try:
        magnitude = unit_registry().Quantity(value, unit).to(target).magnitude
    except PintError as error:
        raise InvalidInput(f"{value} {unit} cannot be expressed in {target}") from error
    return _rounded(float(magnitude))


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(float(value), NORMALISED_DIGITS) + 0.0
