from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import TERM_BASES

from .base import ContractModel
from .citations import AnswerSentence, SourceRef, cited_source_ids
from .subject_keys import TermKey
from .vocabulary import FACT_LEVELS, AnswerLanguage

__all__ = [
    "TERM_BASES",
    "TERM_LABEL_MAX_CHARS",
    "TERM_SCHEMA_VERSION",
    "TERM_SUMMARY_MAX_SENTENCES",
    "WIKIDATA_ID_PATTERN",
    "Term",
    "TermSpan",
    "span_problems",
    "spans_still_shown",
]

TERM_SCHEMA_VERSION = 1
TERM_LABEL_MAX_CHARS = 120
TERM_SUMMARY_MAX_SENTENCES = 3
WIKIDATA_ID_PATTERN = r"^Q[1-9]\d*$"

TermBasis = Literal[*TERM_BASES]


class TermSpan(ContractModel):
    text: str = Field(min_length=1, max_length=TERM_LABEL_MAX_CHARS)
    term_key: TermKey


class Term(ContractModel):
    schema_version: Literal[1]
    key: TermKey
    label: str = Field(min_length=1, max_length=TERM_LABEL_MAX_CHARS)
    language: AnswerLanguage
    local_names: list[str]
    craft_slugs: list[str]
    wikidata_id: str | None = Field(pattern=WIKIDATA_ID_PATTERN)
    basis: TermBasis
    summary: list[AnswerSentence] = Field(min_length=1, max_length=TERM_SUMMARY_MAX_SENTENCES)
    sources: list[SourceRef]
    checked_at: AwareDatetime

    @model_validator(mode="after")
    def _a_cited_summary_of_facts(self) -> Self:
        if len(set(self.local_names)) != len(self.local_names) or any(
            not n.strip() for n in self.local_names
        ):
            raise ValueError(f"term {self.key} lists each local name once")
        if len(set(self.craft_slugs)) != len(self.craft_slugs):
            raise ValueError(f"term {self.key} lists each craft once")
        if any(sentence.level not in FACT_LEVELS for sentence in self.summary):
            raise ValueError(f"term {self.key} summarises facts only, never a hypothesis")
        if [source.id for source in self.sources] != cited_source_ids(self.summary):
            raise ValueError(f"term {self.key} lists every cited source once, in order of first citation")
        return self


def span_problems(text: str, spans: list[TermSpan]) -> list[str]:
    problems: list[str] = []
    keys = [span.term_key for span in spans]
    if len(set(keys)) != len(keys):
        problems.append("each term is marked once")
    taken: list[tuple[int, int]] = []
    for span in spans:
        start = text.find(span.text)
        if start < 0:
            problems.append(f"term {span.term_key} marks {span.text!r}, which is not in the sentence")
            continue
        end = start + len(span.text)
        if _overlaps(start, end, taken):
            problems.append(f"term {span.term_key} overlaps another term")
        taken.append((start, end))
    return problems


def spans_still_shown(text: str, spans: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    kept: list[Mapping[str, Any]] = []
    taken: list[tuple[int, int]] = []
    for span in spans:
        start = text.find(span["text"])
        end = start + len(span["text"])
        if start < 0 or _overlaps(start, end, taken):
            continue
        kept.append(span)
        taken.append((start, end))
    return kept


def _overlaps(start: int, end: int, taken: Sequence[tuple[int, int]]) -> bool:
    return any(start < other_end and other_start < end for other_start, other_end in taken)
