from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

from .quotes import formulas_in, numbers_in
from .sandbox_markup import SandboxProblem

__all__ = [
    "CODE_UNITS",
    "LAYOUT_CONSTANTS",
    "code_number_problems",
    "counter_problems",
    "shown_number_problems",
]

LAYOUT_CONSTANTS = frozenset(
    {float(n) for n in (*range(13), 16, 24, 32, 45, 48, 64, 90, 100, 128, 180, 255, 256, 270, 360, 1000)}
    | {0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.5}
)
CODE_UNITS = frozenset(
    {"px", "em", "rem", "vh", "vw", "vmin", "vmax", "deg", "rad", "turn", "ms", "s", "fr", "ch", "ex", "d"}
)
CODE_NUMERAL = re.compile(r"(?<![\w$.#])(\d++(?:\.\d++)?|\.\d++)([A-Za-z]*+)(?!\.\d)")
OTHER_NOTATION = re.compile(
    r"(?<![\w$.#])(?:0[xXbBoO][\da-fA-F_]++|\d[\d_]*+\.?\d*+[eE][+-]?\d++|\d++_[\d_]++|\d++n)(?![\w$])"
)
FORMULA_NUMBER = re.compile(r"\d{3,}")
COUNTER_DECLARATION = re.compile(r"counter-(?:reset|set|increment)\s*+:([^;}]*+)", re.IGNORECASE)
COUNTER_NUMBER = re.compile(r"(?<![\w.-])[+-]?(\d++(?:\.\d++)?)(?![\w.])")


def shown_number_problems(texts: Iterable[str], data: frozenset[float]) -> Iterator[SandboxProblem]:
    for text in texts:
        for numeral in _shown_numerals(text):
            if _value(numeral) not in data:
                yield SandboxProblem("NUMBER", f"{numeral} shown but not a data value")


def code_number_problems(code: str, data: frozenset[float]) -> Iterator[SandboxProblem]:
    for match in OTHER_NOTATION.finditer(code):
        yield SandboxProblem("NUMBER", f"{match.group(0)} is not a plain decimal")
    for match in CODE_NUMERAL.finditer(code):
        numeral, unit = match.groups()
        if unit in CODE_UNITS:
            continue
        number = float(numeral)
        if number not in LAYOUT_CONSTANTS and number not in data:
            yield SandboxProblem("NUMBER", f"{numeral} is neither a layout constant nor a data value")


def counter_problems(styles: Iterable[str], data: frozenset[float]) -> Iterator[SandboxProblem]:
    for style in styles:
        for declaration in COUNTER_DECLARATION.finditer(style):
            for numeral in COUNTER_NUMBER.findall(declaration.group(1)):
                if float(numeral) not in data:
                    yield SandboxProblem("NUMBER", f"counter value {numeral} is not a data value")


def _shown_numerals(text: str) -> Iterator[str]:
    yield from numbers_in(text)
    for formula in formulas_in(text):
        yield from FORMULA_NUMBER.findall(formula)


def _value(numeral: str) -> float | None:
    try:
        return float(numeral)
    except ValueError:
        return None
