from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.core.errors import InvalidInput
from app.research.elements import ELEMENTS

__all__ = ["ELECTRON", "FORMULA_MAX_CHARS", "HYDRATE_SEPARATORS", "Formula", "hill_formula", "parse_formula"]

ELECTRON = "e^-"
FORMULA_MAX_CHARS = 120
HYDRATE_SEPARATORS = ("·", "•", "*", ".")
CHARGE = re.compile(r"\^(\d*)([+-])$")
LEADING_COUNT = re.compile(r"\d+")
SYMBOL = re.compile(r"[A-Z][a-z]?")
CLOSERS = {"(": ")", "[": "]"}


@dataclass(frozen=True)
class Formula:
    text: str
    counts: Mapping[str, int]
    charge: int

    @property
    def neutral(self) -> bool:
        return self.charge == 0


def parse_formula(text: str) -> Formula:
    written = text.strip()
    if not written or len(written) > FORMULA_MAX_CHARS:
        raise InvalidInput(f"{text!r} is not a formula of 1 to {FORMULA_MAX_CHARS} characters")
    if written == ELECTRON:
        return Formula(text=written, counts=MappingProxyType({}), charge=-1)
    body, charge = _split_charge(written)
    counts: Counter[str] = Counter()
    for part in re.split("|".join(re.escape(s) for s in HYDRATE_SEPARATORS), body):
        counts.update(_part_counts(part, written))
    if not counts:
        raise InvalidInput(f"{text!r} names no element")
    return Formula(text=written, counts=MappingProxyType(dict(sorted(counts.items()))), charge=charge)


def hill_formula(formula: Formula) -> str:
    symbols = sorted(formula.counts)
    if "C" in formula.counts:
        symbols = [
            "C",
            *(["H"] if "H" in formula.counts else []),
            *(s for s in symbols if s not in ("C", "H")),
        ]
    return "".join(f"{s}{formula.counts[s] if formula.counts[s] > 1 else ''}" for s in symbols)


def _split_charge(written: str) -> tuple[str, int]:
    match = CHARGE.search(written)
    if match is None:
        return written, 0
    size = int(match.group(1) or "1")
    if size == 0:
        raise InvalidInput(f"{written!r} carries a zero charge")
    return written[: match.start()], size if match.group(2) == "+" else -size


def _part_counts(part: str, written: str) -> Counter[str]:
    leading = LEADING_COUNT.match(part)
    multiplier = int(leading.group()) if leading else 1
    body = part[leading.end() :] if leading else part
    if multiplier == 0 or not body:
        raise InvalidInput(f"{written!r} has an empty or zero part")
    counts, position = _group(body, 0, None, written)
    if position != len(body):
        raise InvalidInput(f"{written!r} closes a bracket it never opened")
    return Counter({symbol: count * multiplier for symbol, count in counts.items()})


def _group(body: str, position: int, closer: str | None, written: str) -> tuple[Counter[str], int]:
    counts: Counter[str] = Counter()
    while position < len(body) and body[position] not in ")]":
        if body[position] in CLOSERS:
            inner, position = _bracketed(body, position, written)
            counts.update(inner)
            continue
        symbol = SYMBOL.match(body, position)
        if symbol is None or symbol.group() not in ELEMENTS:
            raise InvalidInput(f"{written!r} has no element at {body[position:]!r}")
        count, position = _count(body, symbol.end(), written)
        counts[symbol.group()] += count
    if closer is not None and (position >= len(body) or body[position] != closer):
        raise InvalidInput(f"{written!r} leaves a bracket open")
    return counts, position


def _bracketed(body: str, position: int, written: str) -> tuple[Counter[str], int]:
    closer = CLOSERS[body[position]]
    inner, position = _group(body, position + 1, closer, written)
    count, position = _count(body, position + 1, written)
    return Counter({symbol: number * count for symbol, number in inner.items()}), position


def _count(body: str, position: int, written: str) -> tuple[int, int]:
    digits = LEADING_COUNT.match(body, position)
    if digits is None:
        return 1, position
    count = int(digits.group())
    if count == 0:
        raise InvalidInput(f"{written!r} has a zero count")
    return count, digits.end()
