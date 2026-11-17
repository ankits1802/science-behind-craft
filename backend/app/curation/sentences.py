from __future__ import annotations

import re
from collections.abc import Sequence
from itertools import pairwise

from app.models.enums import CONCEPT_RELATIONS
from app.research.quotes import formulas_in, unsupported_figures
from app.research.translation import protected_tokens

from .limits import BARE_RELATION_SIDE_WORDS_MAX

__all__ = [
    "ABBREVIATIONS",
    "QUALIFYING_WORDS",
    "RELATION_PHRASES",
    "figure_gaps",
    "relationship_sentence",
    "single_sentence",
    "unsourced_hedges",
    "word_count",
]

CLOSERS = "\"')]”’"
OPENERS = "\"'([“‘"
ABBREVIATIONS = frozenset(
    {
        "a.d",
        "approx",
        "b.c",
        "c",
        "ca",
        "capt",
        "cf",
        "co",
        "col",
        "dept",
        "dr",
        "e.g",
        "ed",
        "eds",
        "est",
        "etc",
        "fig",
        "figs",
        "ft",
        "gen",
        "govt",
        "hon",
        "i.e",
        "inc",
        "jr",
        "ltd",
        "mr",
        "mrs",
        "ms",
        "mt",
        "no",
        "nos",
        "pp",
        "prof",
        "pvt",
        "rs",
        "shri",
        "smt",
        "sq",
        "sr",
        "sri",
        "st",
        "u.k",
        "u.s",
        "viz",
        "vol",
        "vols",
        "vs",
    }
)
RELATION_PHRASES = (
    "is used in",
    "are used in",
    "is used by",
    "are used by",
    "is preceded by",
    "are preceded by",
    "preceded by",
    "is followed by",
    "are followed by",
    "followed by",
    "comes before",
    "come before",
    "comes after",
    "come after",
    "is part of",
    "are part of",
    "forms part of",
    "form part of",
    "belongs to",
    "belong to",
    "depends on",
    "depend on",
    "is associated with",
    "are associated with",
    "is similar to",
    "are similar to",
    "contrasts with",
    "contrast with",
    "is produced by",
    "are produced by",
    "uses",
    "use",
    "used",
    "precedes",
    "precede",
    "follows",
    "follow",
    "produces",
    "produce",
    "requires",
    "require",
    "enables",
    "enable",
)
QUALIFYING_WORDS = frozenset(
    {
        "after",
        "although",
        "always",
        "as",
        "because",
        "before",
        "but",
        "by",
        "for",
        "formerly",
        "from",
        "giving",
        "if",
        "instead",
        "into",
        "leaving",
        "mainly",
        "making",
        "mostly",
        "never",
        "no",
        "nor",
        "not",
        "now",
        "often",
        "once",
        "only",
        "rarely",
        "since",
        "so",
        "sometimes",
        "still",
        "than",
        "that",
        "though",
        "to",
        "today",
        "traditionally",
        "unless",
        "until",
        "usually",
        "when",
        "where",
        "whereas",
        "which",
        "while",
        "who",
        "whose",
        "with",
        "without",
    }
)
RELATION = re.compile(
    r"\b(?:"
    + "|".join(re.escape(phrase) for phrase in sorted(RELATION_PHRASES, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)
GRAPH_REFERENCE = re.compile(
    r"\b(?:this|these)\s+(?:materials?|tools?|stages?|steps?|ingredients?|items?)\b(?=\s*(?:\(|\W*$))",
    re.IGNORECASE,
)
GRAPH_FILLER = re.compile(
    r"\bsequential (?:order|steps?|stages?)\b|\(\s*gi method of production\s*\)|\bas documented\W*$|->|\u2192",
    re.IGNORECASE,
)
GRAPH_LABEL = re.compile(r"\b(?:" + "|".join(CONCEPT_RELATIONS) + r")\b")
NOT_BARE = re.compile(r"[\d,;:()]")
HEDGE = re.compile(
    r"\b(?:may|might|could|possibly|probably|perhaps|likely|reportedly|allegedly|apparently|presumably"
    r"|supposedly|purportedly|seemingly|believed|said to|thought to)\b",
    re.IGNORECASE,
)


def word_count(text: str) -> int:
    return len(text.split())


def single_sentence(text: str) -> bool:
    tokens = text.split()
    if not tokens or tokens[-1].rstrip(CLOSERS)[-1:] not in (".", "!", "?"):
        return False
    return not any(_ends_sentence(token, following) for token, following in pairwise(tokens))


def relationship_sentence(text: str) -> bool:
    if GRAPH_REFERENCE.search(text) or GRAPH_FILLER.search(text) or GRAPH_LABEL.search(text):
        return True
    return _bare_relation(text)


def unsourced_hedges(text: str, quotes: Sequence[str]) -> list[str]:
    hedges = dict.fromkeys(found.group().casefold() for found in HEDGE.finditer(text))
    return [hedge for hedge in hedges if not any(_has_words(hedge, quote) for quote in quotes)]


def figure_gaps(text: str, supports: Sequence[str]) -> list[str]:
    stated = {unit for support in supports for unit in _units(support)}
    return [*unsupported_figures(text, supports), *(unit for unit in _units(text) if unit not in stated)]


def _ends_sentence(token: str, following: str) -> bool:
    stripped = token.rstrip(CLOSERS)
    if stripped[-1:] not in (".", "!", "?"):
        return False
    word = stripped[:-1].lstrip(OPENERS).casefold()
    if stripped[-1] == "." and (len(word) <= 1 or word in ABBREVIATIONS):
        return False
    start = following[:1]
    return start.isupper() or start.isdigit() or start in OPENERS


def _bare_relation(text: str) -> bool:
    body = text.strip().rstrip(".!?")
    found = RELATION.search(body)
    if NOT_BARE.search(body) or found is None:
        return False
    sides = (body[: found.start()].split(), body[found.end() :].split())
    return all(
        1 <= len(side) <= BARE_RELATION_SIDE_WORDS_MAX
        and not QUALIFYING_WORDS & {word.casefold() for word in side}
        for side in sides
    )


def _has_words(words: str, text: str) -> bool:
    return re.search(r"\b" + re.escape(words) + r"\b", text, re.IGNORECASE) is not None


def _units(text: str) -> list[str]:
    formulas = set(formulas_in(text))
    return sorted(token for token in protected_tokens(text) if token not in formulas)
