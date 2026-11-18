from __future__ import annotations

import re
from collections.abc import Sequence

from app.research.quotes import figures_in, formulas_in, normalise_quote_text
from app.research.translation import protected_tokens

__all__ = ["DATE_PARTS_MIN", "closed_up", "figure_gaps", "figure_key"]

DATE_PARTS_MIN = 3
LETTER_SPACED = re.compile(r"(?<!\S)\S(?: \S){3,}(?!\S)")
SPACED_DIGITS = re.compile(r"(?<=\d) (?=\d)")
LEADING_ZEROS = re.compile(r"^0+(?=\d)")


def figure_gaps(text: str, supports: Sequence[str]) -> list[str]:
    stated = {figure_key(figure) for support in supports for figure in _stated_figures(support)}
    units = {unit for support in supports for unit in _units(support)}
    return [
        *(figure for figure in figures_in(text) if figure_key(figure) not in stated),
        *(unit for unit in _units(text) if unit not in units),
    ]


def figure_key(figure: str) -> str:
    parts = figure.split(".")
    if len(parts) >= DATE_PARTS_MIN:
        return ".".join(LEADING_ZEROS.sub("", part) for part in parts)
    return LEADING_ZEROS.sub("", figure)


def closed_up(text: str) -> str:
    return LETTER_SPACED.sub(lambda run: SPACED_DIGITS.sub("", run.group()), normalise_quote_text(text))


def _stated_figures(support: str) -> list[str]:
    return [*figures_in(support), *figures_in(closed_up(support))]


def _units(text: str) -> list[str]:
    formulas = set(formulas_in(text))
    return sorted(token for token in protected_tokens(text) if token not in formulas)
