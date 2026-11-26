from __future__ import annotations

import re

from app.research.timeline import BCE_SUFFIX, ordinal

__all__ = ["time_text"]

DATE_PRECISIONS = {9: 4, 10: 7, 11: 10}
DECADE, CENTURY, MILLENNIUM = 8, 7, 6
YEARS_IN = {DECADE: 10, CENTURY: 100, MILLENNIUM: 1000}
SPAN_WORDS = {CENTURY: "century", MILLENNIUM: "millennium"}
XSD_YEAR = re.compile(r"^([+-]?)([0-9]+)-")


def time_text(raw: str, precision: str | None) -> str | None:
    if precision is None or not precision.isdigit():
        return None
    level = int(precision)
    if level in DATE_PRECISIONS:
        sign = "-" if raw.startswith("-") else ""
        return sign + raw.lstrip("+-")[: DATE_PRECISIONS[level]]
    if level in YEARS_IN:
        return _span_text(raw, level)
    return None


def _span_text(raw: str, level: int) -> str | None:
    match = XSD_YEAR.match(raw)
    if match is None:
        return None
    xsd_year = int(match.group(2)) * (-1 if match.group(1) == "-" else 1)
    year = xsd_year if xsd_year > 0 else 1 - xsd_year
    era = "" if xsd_year > 0 else BCE_SUFFIX
    if level == DECADE:
        decade = year // YEARS_IN[DECADE] * YEARS_IN[DECADE]
        return f"{decade}s{era}" if decade else None
    number = -(-year // YEARS_IN[level])
    return f"{ordinal(number)} {SPAN_WORDS[level]}{era}"
