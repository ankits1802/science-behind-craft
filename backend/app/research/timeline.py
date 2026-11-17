from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from types import MappingProxyType

from .quotes import fold_digits, normalise_quote_text, quote_occurs

__all__ = [
    "CENTURY_WORDS",
    "MOVEMENT_WORDS",
    "YEAR_MAX",
    "YEAR_MIN",
    "YearSpan",
    "states_movement",
    "years_named",
    "years_offered",
]

YEAR_MIN = 1000
YEAR_MAX = 2099
YEARS_PER_CENTURY = 100
YEARS_PER_DECADE = 10
CENTURY_WORDS = MappingProxyType(
    {
        "first": 1,
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        "sixth": 6,
        "seventh": 7,
        "eighth": 8,
        "ninth": 9,
        "tenth": 10,
        "eleventh": 11,
        "twelfth": 12,
        "thirteenth": 13,
        "fourteenth": 14,
        "fifteenth": 15,
        "sixteenth": 16,
        "seventeenth": 17,
        "eighteenth": 18,
        "nineteenth": 19,
        "twentieth": 20,
        "twenty-first": 21,
    }
)
MOVEMENT_WORDS = frozenset(
    {
        "arrive",
        "arrived",
        "brought",
        "came",
        "carried",
        "come",
        "exported",
        "fled",
        "imported",
        "invited",
        "migrate",
        "migrated",
        "migration",
        "move",
        "moved",
        "relocate",
        "relocated",
        "sent",
        "settle",
        "settled",
        "shipped",
        "trade",
        "traded",
        "travelled",
        "went",
    }
)

YearSpan = tuple[int, int]

BEFORE_COMMON_ERA = r"(?!\s*(?:B\.?C\.?E?\b|BCE\b))"
YEAR = r"(?<![\d.,])(1\d{3}|20\d{2})(?![\d])"
RANGE = re.compile(
    YEAR + r"\s*(?:-|to)\s*(?:(?:ca|c)\.\s*|circa\s+)?(\d{4}|\d{2})(?![\d])" + BEFORE_COMMON_ERA
)
SINGLE = re.compile(YEAR + r"(?!s\b)" + BEFORE_COMMON_ERA)
DECADE = re.compile(r"(?<![\d.,])(1\d{2}0|20\d0)s\b")
ORDINAL_WORDS = "|".join(sorted(CENTURY_WORDS, key=len, reverse=True))
ORDINAL = rf"(?:(\d{{1,2}})(?:st|nd|rd|th)|({ORDINAL_WORDS}))"
CENTURY = re.compile(
    rf"(?<![\w-]){ORDINAL}(?:\s*-\s*{ORDINAL})?[\s-]+centur(?:y|ies)\b{BEFORE_COMMON_ERA}", re.IGNORECASE
)
WORD = re.compile(r"[^\W\d_]+")
COUNTED = re.compile(r"\s+([a-z]{2,}s)\b")
NOT_COUNTED = frozenset(
    {"across", "as", "has", "his", "is", "its", "less", "plus", "this", "thus", "unless", "was", "whereas"}
)


def years_named(texts: Iterable[str]) -> set[YearSpan]:
    named: set[YearSpan] = set()
    for text in texts:
        plain = fold_digits(normalise_quote_text(text))
        named.update(_ranges(plain))
        named.update((year, year) for year in _singles(plain))
        named.update(_decades(plain))
        named.update(_centuries(plain))
    return named


def years_offered(texts: Iterable[str]) -> set[YearSpan]:
    plain = [fold_digits(normalise_quote_text(text)) for text in texts]
    dated = {year for text in plain for year in _dated_singles(text)}
    return {span for span in years_named(plain) if span[0] != span[1] or span[0] in dated}


def states_movement(texts: Iterable[str], start: str, end: str) -> bool:
    for text in texts:
        folded = text.casefold()
        moves = set(WORD.findall(folded)) & MOVEMENT_WORDS
        if (
            moves
            and quote_occurs(f"from {start.casefold()}", folded)
            and quote_occurs(end.casefold(), folded)
        ):
            return True
    return False


def _ranges(text: str) -> Iterator[YearSpan]:
    for match in RANGE.finditer(text):
        start, tail = int(match.group(1)), match.group(2)
        end = int(tail) if len(tail) == 4 else start - start % YEARS_PER_CENTURY + int(tail)
        if start <= end <= YEAR_MAX:
            yield start, end


def _singles(text: str) -> Iterator[int]:
    for match in SINGLE.finditer(text):
        year = int(match.group(1))
        if YEAR_MIN <= year <= YEAR_MAX:
            yield year


def _dated_singles(text: str) -> Iterator[int]:
    for match in SINGLE.finditer(text):
        counted = COUNTED.match(text, match.end())
        if counted is None or counted.group(1) in NOT_COUNTED:
            yield int(match.group(1))


def _decades(text: str) -> Iterator[YearSpan]:
    for match in DECADE.finditer(text):
        start = int(match.group(1))
        yield start, start + YEARS_PER_DECADE - 1


def _centuries(text: str) -> Iterator[YearSpan]:
    for match in CENTURY.finditer(text):
        first = _century(match.group(1), match.group(2))
        last = _century(match.group(3), match.group(4)) or first
        if first and last and first <= last:
            yield (first - 1) * YEARS_PER_CENTURY + 1, last * YEARS_PER_CENTURY


def _century(digits: str | None, word: str | None) -> int | None:
    if digits:
        return int(digits) or None
    if word:
        return CENTURY_WORDS[word.casefold()]
    return None
