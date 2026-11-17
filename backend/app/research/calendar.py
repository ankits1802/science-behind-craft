from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from types import MappingProxyType

__all__ = [
    "EXCLUDING_WORDS",
    "EXCLUDING_WORDS_BEFORE",
    "MAPPING_WORDS_AFTER",
    "MAPPING_WORDS_BEFORE",
    "MONTHS",
    "MONTH_NAMES",
    "SEASONS",
    "SEASON_WORDS",
    "months_named",
    "only_season",
    "season_months",
    "seasons_named",
    "year_months",
]

MONTHS = 12
MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
SEASONS = ("MONSOON", "WINTER", "SUMMER")
SEASON_WORDS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "MONSOON": ("monsoon", "rainy season", "rains"),
        "WINTER": ("winter", "cold season"),
        "SUMMER": ("summer", "hot season"),
    }
)
AMBIGUOUS_MONTH = "May"
SENTENCE_START = re.compile(r"(?:^|[.!?;:]\s*)$")
MONTH = re.compile(
    r"\b(" + "|".join(name for month in MONTH_NAMES for name in (month, month[:3])) + r"|Sept)\.?(?![a-z])"
)
RANGE_JOIN = re.compile(r"^\s*(?:to|till|until|through|-|–|—)\s*$")
DAY_OR_YEAR_AFTER = re.compile(r"^[\s,/-]*(?:\d{4}|\d{1,2}(?:st|nd|rd|th)?)\b")
DAY_BEFORE = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?[\s,/-]*$")
CLAUSE_BREAK = re.compile(r"[.;:!?]")
WORD = re.compile(r"\w+")
SPAN_WORDS_AFTER = frozenset(
    {
        "months",
        "month",
        "season",
        "period",
        "rain",
        "rainfall",
        "of",
        "from",
        "between",
        "is",
        "are",
        "lasts",
        "runs",
        "spans",
        "extends",
        "falls",
        "fall",
        "comes",
        "brings",
        "bringing",
        "the",
        "its",
        "in",
        "with",
        "usually",
        "typically",
        "roughly",
        "about",
        "around",
        "mm",
        "cm",
    }
)
SPAN_WORDS_BEFORE = frozenset({"the", "a", "is", "are", "its", "of", "in"})
POINT_WORDS = frozenset(
    {
        "after",
        "before",
        "until",
        "till",
        "since",
        "outside",
        "except",
        "unlike",
        "beyond",
        "following",
        "preceding",
        "end",
        "start",
        "onset",
        "beginning",
        "early",
        "late",
        "mid",
    }
)
SEASON_PATTERNS: Mapping[str, re.Pattern[str]] = MappingProxyType(
    {
        season: re.compile(
            r"(?<!-)\b(?:" + "|".join(re.escape(word) for word in words) + r")\b", re.IGNORECASE
        )
        for season, words in SEASON_WORDS.items()
    }
)
EXCLUDING_WORDS = POINT_WORDS | frozenset(
    {
        "not",
        "no",
        "never",
        "nor",
        "neither",
        "without",
        "avoid",
        "avoided",
        "avoids",
        "stop",
        "stops",
        "stopped",
    }
)
NEGATION = "not"
CONTRACTED_NOT = "n't"
POINT_CLAUSE = re.compile(r"[,.;:!?(]")
CLAUSE_TOKEN = re.compile(r"[\w'’]+")
BARE_ABBREVIATIONS = frozenset({"Jan", "Mar", "Dec"})
NAME_AFTER = re.compile(r"\s+[A-Z]")
MAPPING_WORDS_AFTER = 8
MAPPING_WORDS_BEFORE = 3
POINT_WORDS_BEFORE = 3
EXCLUDING_WORDS_BEFORE = 5


@dataclass(frozen=True)
class _Span:
    start: int
    end: int


@dataclass(frozen=True)
class _Mention(_Span):
    month: int


@dataclass(frozen=True)
class _Range(_Span):
    months: frozenset[int]


@dataclass(frozen=True)
class _SeasonMention(_Span):
    season: str


def months_named(texts: Iterable[str]) -> frozenset[int]:
    named: set[int] = set()
    for text in texts:
        named |= _months(text, _mentions(text))
    return frozenset(named)


def year_months(texts: Iterable[str]) -> frozenset[int]:
    named: set[int] = set()
    for text in texts:
        named |= _timed_months(text, _undated(text))
    return frozenset(named)


def seasons_named(texts: Iterable[str]) -> frozenset[str]:
    return frozenset(mention.season for text in texts for mention in _season_mentions(text))


def only_season(text: str) -> str | None:
    mentions = _season_mentions(text)
    named = {mention.season for mention in mentions}
    if len(named) != 1 or any(_excluded(text, mention.start) for mention in mentions):
        return None
    return next(iter(named))


def season_months(text: str) -> dict[str, frozenset[int]]:
    found = _SeasonText(text)
    taken: dict[_SeasonMention, _Range] = {}
    for look in (found.after, found.before):
        for mention in found.mentions:
            span = None if mention in taken else look(mention)
            if span is not None and span not in taken.values():
                taken[mention] = span
    stated: dict[str, set[frozenset[int]]] = {}
    for mention, span in taken.items():
        stated.setdefault(mention.season, set()).add(span.months)
    return {season: next(iter(spans)) for season, spans in stated.items() if len(spans) == 1}


def _mentions(text: str) -> list[_Mention]:
    return [
        _Mention(match.start(), match.end(), _month_number(match.group(1)))
        for match in MONTH.finditer(text)
        if not _modal_may(text, match) and not _a_name(text, match)
    ]


def _undated(text: str) -> list[_Mention]:
    return [
        mention
        for mention in _mentions(text)
        if not DAY_OR_YEAR_AFTER.match(text[mention.end :]) and not DAY_BEFORE.search(text[: mention.start])
    ]


def _months(text: str, mentions: Sequence[_Mention]) -> set[int]:
    months = {mention.month for mention in mentions}
    for found in _joined(text, mentions):
        months |= found.months
    return months


def _timed_months(text: str, mentions: Sequence[_Mention]) -> set[int]:
    ranges = _joined(text, mentions)
    months: set[int] = set()
    for span in ranges:
        if not _excluded(text, span.start):
            months |= span.months
    for mention in mentions:
        ranged = any(span.start <= mention.start < span.end for span in ranges)
        if not ranged and not _excluded(text, mention.start):
            months.add(mention.month)
    return months


def _excluded(text: str, start: int) -> bool:
    return bool(EXCLUDING_WORDS.intersection(_clause_words(text, start, EXCLUDING_WORDS_BEFORE)))


def _clause_words(text: str, start: int, most: int) -> list[str]:
    clause = POINT_CLAUSE.split(text[:start])[-1]
    return [_clause_word(token) for token in CLAUSE_TOKEN.findall(clause)][-most:]


def _clause_word(token: str) -> str:
    folded = token.casefold().replace("’", "'")
    return NEGATION if folded.endswith(CONTRACTED_NOT) else folded


def _ranges(text: str) -> list[_Range]:
    return _joined(text, _undated(text))


def _joined(text: str, mentions: Sequence[_Mention]) -> list[_Range]:
    return [
        _Range(first.start, last.end, frozenset(_months_between(first.month, last.month)))
        for first, last in pairwise(mentions)
        if RANGE_JOIN.match(text[first.end : last.start])
    ]


def _season_mentions(text: str) -> list[_SeasonMention]:
    found = [
        _SeasonMention(match.start(), match.end(), season)
        for season, pattern in SEASON_PATTERNS.items()
        for match in pattern.finditer(text)
    ]
    return sorted(found, key=lambda mention: mention.start)


class _SeasonText:
    def __init__(self, text: str) -> None:
        self.text = text
        self.ranges = _ranges(text)
        self.mentions = _season_mentions(text)

    def after(self, mention: _SeasonMention) -> _Range | None:
        span = next((span for span in self.ranges if span.start >= mention.end), None)
        if span is None or self._a_point(mention):
            return None
        gap = _Span(mention.end, span.start)
        return span if self._joins(gap, SPAN_WORDS_AFTER, MAPPING_WORDS_AFTER) else None

    def before(self, mention: _SeasonMention) -> _Range | None:
        span = next((span for span in reversed(self.ranges) if span.end <= mention.start), None)
        if span is None or self._a_point(mention):
            return None
        gap = _Span(span.end, mention.start)
        return span if self._joins(gap, SPAN_WORDS_BEFORE, MAPPING_WORDS_BEFORE) else None

    def _a_point(self, mention: _SeasonMention) -> bool:
        return bool(POINT_WORDS.intersection(_clause_words(self.text, mention.start, POINT_WORDS_BEFORE)))

    def _joins(self, gap: _Span, allowed: frozenset[str], most_words: int) -> bool:
        between = self.text[gap.start : gap.end]
        words = [word.casefold() for word in WORD.findall(between)]
        if CLAUSE_BREAK.search(between) or len(words) > most_words:
            return False
        if any(word not in allowed and not any(c.isdigit() for c in word) for word in words):
            return False
        return not any(gap.start <= other.start < gap.end for other in self.mentions)


def _month_number(name: str) -> int:
    short = "Sep" if name == "Sept" else name[:3]
    return next(index for index, month in enumerate(MONTH_NAMES, 1) if month.startswith(short))


def _a_name(text: str, match: re.Match[str]) -> bool:
    return match.group(0) in BARE_ABBREVIATIONS and NAME_AFTER.match(text, match.end()) is not None


def _modal_may(text: str, match: re.Match[str]) -> bool:
    return match.group(1) == AMBIGUOUS_MONTH and SENTENCE_START.search(text[: match.start()]) is not None


def _months_between(first: int, last: int) -> set[int]:
    span = (last - first) % MONTHS
    return {(first - 1 + step) % MONTHS + 1 for step in range(span + 1)}
