from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import pairwise
from typing import Literal

from .quotes import quote_key, spans_in_key

__all__ = ["ALTERNATIVE_GAP_WORDS_MAX", "ALTERNATIVE_WORDS", "alternatives_named"]

ALTERNATIVE_WORDS = re.compile(
    r"(?<!\w)(?:or|instead|rather|versus|vs|replac\w*|supersed\w*|substitut\w*|alternatively)(?!\w)"
)
LIST_GAP = re.compile(r"[\s,;/]*")
ALTERNATIVE_GAP_WORDS_MAX = 3

Gap = Literal["ALTERNATIVE", "LIST"]


@dataclass(frozen=True)
class _Mention:
    start: int
    end: int
    name: str


def alternatives_named(text: str, names: Mapping[str, Iterable[str]]) -> list[frozenset[str]]:
    key = quote_key(text.casefold())
    mentions = _mentions(key, names)
    found: list[frozenset[str]] = []
    run: set[str] = set()
    offered = False
    for before, after in pairwise(mentions):
        gap = _gap(key[before.end : after.start])
        if gap is None:
            _close(found, run, offered=offered)
            run, offered = set(), False
            continue
        run |= {before.name, after.name}
        offered = offered or gap == "ALTERNATIVE"
    _close(found, run, offered=offered)
    return found


def _mentions(key: str, names: Mapping[str, Iterable[str]]) -> list[_Mention]:
    every = sorted(
        (
            _Mention(start, end, name)
            for name, surfaces in names.items()
            for surface in dict.fromkeys(s.casefold() for s in surfaces if s.strip())
            for start, end in spans_in_key(surface, key)
        ),
        key=lambda mention: (mention.start, mention.start - mention.end, mention.name),
    )
    kept: list[_Mention] = []
    for mention in every:
        if not kept or mention.start >= kept[-1].end:
            kept.append(mention)
    return kept


def _gap(between: str) -> Gap | None:
    if LIST_GAP.fullmatch(between):
        return "LIST"
    if len(between.split()) <= ALTERNATIVE_GAP_WORDS_MAX and ALTERNATIVE_WORDS.search(between):
        return "ALTERNATIVE"
    return None


def _close(found: list[frozenset[str]], run: set[str], *, offered: bool) -> None:
    if offered and len(run) >= 2:
        found.append(frozenset(run))
