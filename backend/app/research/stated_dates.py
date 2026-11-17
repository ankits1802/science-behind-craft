from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from datetime import date

from .calendar import MONTH_NAMES
from .quotes import figures_in

__all__ = [
    "DATE_PRECISIONS",
    "first_day_date",
    "stated_dates",
    "stated_precision",
    "states_date",
]

YEAR_CHARS = 4
MONTH_CHARS = 7
DAY_CHARS = 10
DATE_PRECISIONS = (DAY_CHARS, MONTH_CHARS, YEAR_CHARS)
MONTH = "|".join(name for month in MONTH_NAMES for name in (month, month[:3])) + "|Sept"
DAY_DATES = (
    re.compile(r"(?<![\d-])(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})(?![\d-])"),
    re.compile(r"(?<!\d)(?P<d>\d{1,2})[-/.](?P<m>\d{1,2})[-/.](?P<y>\d{4})(?!\d)"),
    re.compile(
        rf"(?<!\d)(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<mon>{MONTH})\.?,?\s+(?P<y>\d{{4}})(?!\d)", re.I
    ),
    re.compile(rf"\b(?P<mon>{MONTH})\.?\s+(?P<d>\d{{1,2}})(?:st|nd|rd|th)?,?\s+(?P<y>\d{{4}})(?!\d)", re.I),
)
MONTH_DATES = (re.compile(rf"\b(?P<mon>{MONTH})\.?,?\s+(?P<y>\d{{4}})(?!\d)"),)


def stated_dates(text: str) -> list[str]:
    days = _every(DAY_DATES, text)
    inside = [match.span() for match in days]
    months = [m for m in _every(MONTH_DATES, text) if not any(a <= m.start() < b for a, b in inside)]
    found = [(match.start(), _day(match)) for match in days]
    found += [(match.start(), _month_of_year(match)) for match in months]
    return list(dict.fromkeys(iso for _, iso in sorted(found, key=lambda pair: pair[0]) if iso))


def first_day_date(text: str) -> str | None:
    found = sorted(_every(DAY_DATES, text), key=lambda match: match.start())
    return _day(found[0]) if found else None


def states_date(value: str, texts: Iterable[str]) -> bool:
    if len(value) == YEAR_CHARS:
        return any(value in figures_in(text) for text in texts)
    return any(stated[: len(value)] == value for text in texts for stated in stated_dates(text))


def stated_precision(value: str, texts: Sequence[str]) -> str | None:
    return next(
        (value[:size] for size in DATE_PRECISIONS if size <= len(value) and states_date(value[:size], texts)),
        None,
    )


def _every(patterns: Sequence[re.Pattern[str]], text: str) -> list[re.Match[str]]:
    return [match for pattern in patterns for match in pattern.finditer(text)]


def _day(match: re.Match[str]) -> str | None:
    try:
        return date(int(match.group("y")), _month(match), int(match.group("d"))).isoformat()
    except ValueError:
        return None


def _month_of_year(match: re.Match[str]) -> str | None:
    try:
        return date(int(match.group("y")), _month(match), 1).isoformat()[:MONTH_CHARS]
    except ValueError:
        return None


def _month(match: re.Match[str]) -> int:
    if "mon" not in match.groupdict():
        return int(match.group("m"))
    short = match.group("mon").casefold()[:3]
    return next(n for n, month in enumerate(MONTH_NAMES, start=1) if month.casefold().startswith(short))
