from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from app.models.enums import (
    CONTRIBUTION_STATUSES,
    CREDIT_MODES,
    DISCIPLINES,
    EXTRACTION_STATUSES,
    INTERVIEW_TOPICS,
    LOCATOR_PRECISIONS,
    TESTIMONY_CONCEPT_TYPES,
    TESTIMONY_ENGLISH_SOURCES,
    TESTIMONY_REJECT_REASONS,
    TESTIMONY_SCREENS,
)
from app.models.knowledge import QUOTE_MAX_CHARS

from .evidence import personal_data_in
from .quotes import QUOTE_MIN_CHARS, figures_in

__all__ = [
    "ARTISAN_CRAFTS_MAX",
    "AUDIO_LINK_SECONDS",
    "CLAIM_TEXT_MAX",
    "CONCEPT_NAME_MAX",
    "CONTRIBUTIONS_PER_CONVERSATION_MAX",
    "CONTRIBUTION_MOVES",
    "CONTRIBUTION_STATUSES",
    "CORROBORATING_CLAIMS_MAX",
    "CREDIT_MODES",
    "CREDIT_NAME_MAX",
    "CREDIT_SHORT_NAME_MAX",
    "ENGLISH_MAX",
    "EXTRACTION_CALLS_MAX",
    "EXTRACTION_PART_CHARACTERS",
    "EXTRACTION_STATUSES",
    "INTERVIEW_TOPICS",
    "LOCATOR_PRECISIONS",
    "NAME_HELD_BACK",
    "QUOTE_MAX_CHARS",
    "QUOTE_MIN_CHARS",
    "RECORDING_NOTICE_VERSION",
    "REVIEW_NOTE_MAX",
    "SPEAKER_ROLE",
    "TESTIMONY_CONCEPT_TYPES",
    "TESTIMONY_ENGLISH_SOURCES",
    "TESTIMONY_REJECT_REASONS",
    "TESTIMONY_RETENTION_DAYS",
    "TESTIMONY_SCREENS",
    "ContributionStatus",
    "CreditMode",
    "Draft",
    "EnglishSource",
    "InterviewTopic",
    "LocatorPrecision",
    "RejectReason",
    "Speaker",
    "contribution_problems",
    "credit_name_problem",
    "held_back_terms",
    "move_allowed",
    "quote_span",
    "screens_for",
    "speaker",
    "time_locator",
]

ContributionStatus = Literal[*CONTRIBUTION_STATUSES]
CreditMode = Literal[*CREDIT_MODES]
EnglishSource = Literal[*TESTIMONY_ENGLISH_SOURCES]
InterviewTopic = Literal[*INTERVIEW_TOPICS]
LocatorPrecision = Literal[*LOCATOR_PRECISIONS]
RejectReason = Literal[*TESTIMONY_REJECT_REASONS]

ARTISAN_CRAFTS_MAX = 12
CREDIT_NAME_MAX = 120
CREDIT_SHORT_NAME_MAX = 60
CONTRIBUTIONS_PER_CONVERSATION_MAX = 30
EXTRACTION_PART_CHARACTERS = 40_000
EXTRACTION_CALLS_MAX = 3
CLAIM_TEXT_MAX = 300
ENGLISH_MAX = 600
CONCEPT_NAME_MAX = 120
REVIEW_NOTE_MAX = 500
CORROBORATING_CLAIMS_MAX = 5
TESTIMONY_RETENTION_DAYS = 30
AUDIO_LINK_SECONDS = 900
NAME_HELD_BACK = "NAME_HELD_BACK"
RECORDING_NOTICE_VERSION = "2026-11-18"
SPEAKER_ROLE = "ARTISAN"
HELD_BACK_TERM_MIN_LETTERS = 3
CREDIT_NAME_PUNCTUATION = frozenset(" .'-")
WORD_CATEGORIES = frozenset("LMN")
NAME_CATEGORIES = frozenset("LM")
WORD_JOINERS = frozenset("‌‍")
NAME_JOINERS = "'’-"

CONTRIBUTION_MOVES: frozenset[tuple[str, str]] = frozenset(
    {
        ("PENDING", "APPROVED"),
        ("PENDING", "REJECTED"),
        ("PENDING", "WITHDRAWN"),
        ("APPROVED", "APPROVED"),
        ("APPROVED", "REJECTED"),
        ("APPROVED", "WITHDRAWN"),
    }
)


@dataclass(frozen=True, kw_only=True)
class Speaker:
    name: str | None
    role: str
    district: str
    state: str
    line: str


@dataclass(frozen=True, kw_only=True)
class Draft:
    quote: str
    english: str
    claim: str
    discipline: str
    concept_type: str
    concept_name: str


def move_allowed(source: str, target: str) -> bool:
    return (source, target) in CONTRIBUTION_MOVES


def speaker(
    *,
    mode: str,
    name: str | None,
    short_name: str | None,
    craft: str,
    district: str,
    state: str,
) -> Speaker:
    shown = {"FULL_NAME": name, "FIRST_NAME": short_name}.get(mode)
    if shown:
        line = f"{shown}, {craft}, {district}, {state}"
    else:
        shown = None
        line = f"An artisan of {craft}, {district}, {state}"
    return Speaker(name=shown, role=SPEAKER_ROLE, district=district, state=state, line=line)


def time_locator(start_ms: int, end_ms: int, precision: str) -> str:
    if precision == "TURN":
        return f"at {_clock(start_ms)}"
    return f"{_clock(start_ms)}–{_clock(end_ms)}"


def _clock(ms: int) -> str:
    seconds = max(ms, 0) // 1000
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def credit_name_problem(name: str | None, *, limit: int) -> str | None:
    text = unicodedata.normalize("NFC", name or "").strip()
    if not text:
        return "Give the name to show, or choose to be credited by craft and district."
    if len(text) > limit:
        return f"A name to show is at most {limit} characters."
    if personal_data_in(text):
        return "A name to show holds no email address, phone or identity number."
    for character in text:
        if character in CREDIT_NAME_PUNCTUATION or unicodedata.category(character)[0] in {"L", "M"}:
            continue
        return "A name to show uses letters, spaces, full stops, apostrophes and hyphens only."
    return None


def held_back_terms(
    *, account_name: str, mode: str, credit_name: str | None, short_name: str | None
) -> frozenset[str]:
    if mode == "FULL_NAME":
        return frozenset()
    terms = _name_words(account_name) | _name_words(credit_name or "")
    if mode == "FIRST_NAME":
        terms -= _name_words(short_name or "")
    return frozenset(term for term in terms if len(term) >= HELD_BACK_TERM_MIN_LETTERS)


def _is_word_character(character: str) -> bool:
    return character in WORD_JOINERS or unicodedata.category(character)[0] in WORD_CATEGORIES


def _is_name_character(character: str) -> bool:
    return character in WORD_JOINERS or unicodedata.category(character)[0] in NAME_CATEGORIES


def _name_words(text: str) -> frozenset[str]:
    folded = _folded(text)
    marked = "".join(
        character if _is_name_character(character) or character in NAME_JOINERS else " "
        for character in folded
    )
    words = (word.strip(NAME_JOINERS) for word in marked.split())
    return frozenset(word for word in words if word)


def _folded(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold()


def _stands_alone(text: str, start: int, end: int) -> bool:
    before = start > 0 and _is_word_character(text[start - 1])
    after = end < len(text) and _is_word_character(text[end])
    return not before and not after


def _holds_word(text: str, term: str) -> bool:
    start = text.find(term)
    while start != -1:
        if _stands_alone(text, start, start + len(term)):
            return True
        start = text.find(term, start + 1)
    return False


def screens_for(texts: Iterable[str | None], terms: frozenset[str]) -> list[str]:
    folded = [_folded(text) for text in texts if text]
    for term in terms:
        if any(_holds_word(text, term) for text in folded):
            return [NAME_HELD_BACK]
    return []


def quote_span(quote: str, turn_text: str, *, near: int | None = None) -> tuple[int, int] | None:
    needle = unicodedata.normalize("NFC", quote)
    haystack = unicodedata.normalize("NFC", turn_text)
    starts = [m.start() for m in re.finditer(re.escape(needle), haystack)] if needle else []
    spans = [
        (start, start + len(needle)) for start in starts if _on_word_boundaries(haystack, start, len(needle))
    ]
    if not spans:
        return None
    if near is None:
        return spans[0]
    return min(spans, key=lambda span: abs(span[0] - near))


def _on_word_boundaries(text: str, start: int, length: int) -> bool:
    end = start + length
    last = end - 1
    while last > start and unicodedata.category(text[last])[0] == "P":
        last -= 1
    starts_on_base = unicodedata.category(text[start])[0] in "LN"
    return starts_on_base and _is_word_character(text[last]) and _stands_alone(text, start, end)


def contribution_problems(draft: Draft, turn_text: str) -> list[str]:
    problems: list[str] = []
    quote = unicodedata.normalize("NFC", draft.quote)
    if not QUOTE_MIN_CHARS <= len(quote) <= QUOTE_MAX_CHARS:
        problems.append(f"the quote is {QUOTE_MIN_CHARS} to {QUOTE_MAX_CHARS} characters")
    if quote_span(quote, turn_text) is None:
        problems.append("the quote is the artisan's exact words from the turn, on whole words")
    if not 1 <= len(draft.english) <= ENGLISH_MAX:
        problems.append(f"the English is 1 to {ENGLISH_MAX} characters")
    if sorted(figures_in(draft.english)) != sorted(figures_in(quote)):
        problems.append("the English carries exactly the figures of the quote")
    if not 1 <= len(draft.claim) <= CLAIM_TEXT_MAX:
        problems.append(f"the claim is 1 to {CLAIM_TEXT_MAX} characters")
    if set(figures_in(draft.claim)) - set(figures_in(quote)):
        problems.append("every figure of the claim is in the quote")
    if any(personal_data_in(text) for text in (quote, draft.english, draft.claim)):
        problems.append("no email address, phone or identity number")
    if draft.discipline not in DISCIPLINES:
        problems.append(f"the field {draft.discipline!r} is one of the disciplines")
    if draft.concept_type not in TESTIMONY_CONCEPT_TYPES:
        problems.append(f"the concept type {draft.concept_type!r} is one testimony may have")
    if not 1 <= len(draft.concept_name.strip()) <= CONCEPT_NAME_MAX:
        problems.append(f"the concept name is 1 to {CONCEPT_NAME_MAX} characters")
    return problems
