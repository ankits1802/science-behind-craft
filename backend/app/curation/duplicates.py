from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from itertools import combinations

from rapidfuzz import fuzz

from .limits import NEAR_DUPLICATE_MIN_SCORE
from .matching import match_key

__all__ = ["DuplicatePair", "duplicate_key", "near_duplicates"]

NON_WORD = re.compile(r"[\W_]+")


@dataclass(frozen=True)
class DuplicatePair:
    first: str
    second: str
    score: float


def duplicate_key(text: str) -> str:
    return NON_WORD.sub(" ", match_key(text)).strip()


def near_duplicates(
    texts: Sequence[tuple[str, str]], *, linked: Collection[frozenset[str]] = ()
) -> list[DuplicatePair]:
    keys = [(item_id, duplicate_key(text)) for item_id, text in texts]
    found = []
    for (first, first_key), (second, second_key) in combinations(keys, 2):
        if frozenset((first, second)) in linked:
            continue
        score = max(fuzz.ratio(first_key, second_key), fuzz.token_sort_ratio(first_key, second_key))
        if score >= NEAR_DUPLICATE_MIN_SCORE:
            found.append(DuplicatePair(first, second, round(score, 1)))
    return found
