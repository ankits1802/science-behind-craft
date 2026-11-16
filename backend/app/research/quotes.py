from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

__all__ = [
    "QUOTE_MIN_CHARS",
    "QUOTE_OVERLAP_MIN",
    "figures_in",
    "normalise_quote_text",
    "quote_key",
    "quote_occurs",
    "quote_overlap",
    "trivial_quote",
    "unsupported_figures",
]

QUOTE_MIN_CHARS = 20
QUOTE_OVERLAP_MIN = 0.5
STEM_CHARS = 4

SOFT_HYPHEN = chr(0x00AD)
DASH_CODEPOINTS = (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2212)
SINGLE_QUOTE_CODEPOINTS = (0x2018, 0x2019, 0x201A, 0x201B)
DOUBLE_QUOTE_CODEPOINTS = (0x201C, 0x201D, 0x201E, 0x201F)
TYPOGRAPHIC = str.maketrans(
    {chr(c): "-" for c in DASH_CODEPOINTS}
    | {chr(c): "'" for c in SINGLE_QUOTE_CODEPOINTS}
    | {chr(c): '"' for c in DOUBLE_QUOTE_CODEPOINTS}
)
LINE_BREAK_HYPHEN = re.compile(r"(\w)-[ \t]*\r?\n\s*(\w)")
WHITESPACE = re.compile(r"\s+")
FORMULA = re.compile(r"(?<![A-Za-z0-9])(?:[A-Z][a-z]?\d*|\((?:[A-Z][a-z]?\d*)+\)\d*)+(?![A-Za-z0-9])")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
WORD_HYPHEN = re.compile(r"(?<=[^\W\d_])-(?=[^\W\d_])")
CONTENT_WORD = re.compile(r"[^\W\d_]{4,}")
OPEN_BOUNDARY = r"(?<!\w)(?<!\d[.,])"
CLOSE_BOUNDARY = r"(?!\w)(?![.,]\d)"
STOP_WORDS = frozenset(
    {
        "about",
        "after",
        "also",
        "been",
        "before",
        "being",
        "both",
        "could",
        "does",
        "done",
        "each",
        "from",
        "have",
        "having",
        "into",
        "more",
        "most",
        "much",
        "must",
        "only",
        "onto",
        "other",
        "over",
        "same",
        "should",
        "some",
        "such",
        "than",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "under",
        "very",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "will",
        "with",
        "within",
        "would",
        "your",
    }
)


def normalise_quote_text(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).replace(SOFT_HYPHEN, "")
    joined = LINE_BREAK_HYPHEN.sub(r"\1\2", folded)
    return WHITESPACE.sub(" ", joined.translate(TYPOGRAPHIC)).strip()


def quote_key(text: str) -> str:
    return WORD_HYPHEN.sub("", normalise_quote_text(text))


def quote_occurs(quote: str, text: str) -> bool:
    needle = quote_key(quote)
    if not needle:
        return False
    opening = OPEN_BOUNDARY if needle[0].isalnum() else ""
    closing = CLOSE_BOUNDARY if needle[-1].isalnum() else ""
    return re.search(opening + re.escape(needle) + closing, quote_key(text)) is not None


def trivial_quote(quote: str) -> bool:
    return len(quote_key(quote)) < QUOTE_MIN_CHARS


def quote_overlap(text: str, quotes: Iterable[str]) -> float:
    wanted = _content_stems(text)
    if not wanted:
        return 0.0
    found = {stem for quote in quotes for stem in _content_stems(quote)}
    return len(wanted & found) / len(wanted)


def figures_in(text: str) -> list[str]:
    normalised = normalise_quote_text(text)
    formulas = [m.group() for m in FORMULA.finditer(normalised) if any(ch.isdigit() for ch in m.group())]
    rest = FORMULA.sub(" ", normalised)
    numbers = [m.group().replace(",", "") for m in NUMBER.finditer(rest)]
    return list(dict.fromkeys([*formulas, *numbers]))


def unsupported_figures(text: str, cited_texts: Iterable[str]) -> list[str]:
    supported = {figure for cited in cited_texts for figure in figures_in(cited)}
    return [figure for figure in figures_in(text) if figure not in supported]


def _content_stems(text: str) -> set[str]:
    words = (word.casefold() for word in CONTENT_WORD.findall(quote_key(text)))
    return {word[:STEM_CHARS] for word in words if word not in STOP_WORDS}
