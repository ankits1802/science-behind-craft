from __future__ import annotations

import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.core.errors import ExternalFailure
from app.research.composition import (
    FOLLOW_UPS_MAX,
    HEADING_MAX_CHARS,
    ComposeCandidate,
    ComposedSentence,
    QuotedSpan,
    sentence_violations,
)
from app.research.evidence import personal_data_in
from app.research.quotes import figures_in
from app.research.structured import MODEL_SERVICE

__all__ = [
    "DraftAnswer",
    "DraftSection",
    "DraftSentence",
    "checked_sentence",
    "free_text_problem",
    "parsed_answer",
    "parsed_replacements",
]

LINK_OR_MARKUP = re.compile(r"https?:|www\.|<|>|\]\(", re.IGNORECASE)


@dataclass(frozen=True)
class DraftSentence:
    heading: str
    raw_text: str
    sentence: ComposedSentence | None
    problems: tuple[str, ...]

    @property
    def passes(self) -> bool:
        return self.sentence is not None and not self.problems

    @property
    def problem_kinds(self) -> tuple[str, ...]:
        return tuple(problem.split(":", 1)[0] for problem in self.problems)


@dataclass(frozen=True)
class DraftSection:
    heading: str
    sentences: tuple[DraftSentence, ...]


@dataclass(frozen=True)
class DraftAnswer:
    sections: tuple[DraftSection, ...]
    follow_ups: tuple[str, ...]

    @property
    def failed(self) -> list[DraftSentence]:
        return [s for section in self.sections for s in section.sentences if not s.passes]


def parsed_answer(reply: Mapping[str, Any], allowed: Mapping[str, ComposeCandidate]) -> DraftAnswer:
    sections = _list(reply, "sections")
    follow_ups = _list(reply, "followUps")
    return DraftAnswer(
        sections=tuple(_section(raw, allowed) for raw in sections),
        follow_ups=tuple(_usable_follow_ups(follow_ups)),
    )


def parsed_replacements(
    reply: Mapping[str, Any], failed: int, allowed: Mapping[str, ComposeCandidate]
) -> dict[int, DraftSentence]:
    replacements: dict[int, DraftSentence] = {}
    for raw in _list(reply, "sentences"):
        index = raw.get("index") if isinstance(raw, Mapping) else None
        if isinstance(index, int) and 0 <= index < failed and index not in replacements:
            replacements[index] = checked_sentence(raw, "", allowed)
    return replacements


def checked_sentence(raw: Any, heading: str, allowed: Mapping[str, ComposeCandidate]) -> DraftSentence:
    raw_text = str(raw.get("text", "")) if isinstance(raw, Mapping) else str(raw)
    try:
        sentence = _sentence(raw, allowed)
    except (ValidationError, TypeError, AttributeError, KeyError, ValueError) as error:
        return DraftSentence(heading, raw_text, None, (f"MALFORMED: {_reason(error)}",))
    problems = tuple(f"{v.kind}: {v.detail}" for v in sentence_violations(sentence, allowed))
    return DraftSentence(heading, raw_text, sentence, problems)


def free_text_problem(text: str) -> str | None:
    if LINK_OR_MARKUP.search(text):
        return "carries a link or markup"
    found = personal_data_in(text)
    if found:
        return f"carries personal data ({', '.join(found)})"
    return None


def _section(raw: Any, allowed: Mapping[str, ComposeCandidate]) -> DraftSection:
    if not isinstance(raw, Mapping):
        raise _unusable("a section is not an object")
    heading = str(raw.get("heading", "")).strip()
    problem = _heading_problem(heading)
    if problem:
        raise _unusable(f"a section heading {problem}")
    sentences = _list(raw, "sentences")
    return DraftSection(heading, tuple(checked_sentence(s, heading, allowed) for s in sentences))


def _sentence(raw: Mapping[str, Any], allowed: Mapping[str, ComposeCandidate]) -> ComposedSentence:
    spans = [QuotedSpan(ref=str(q["source"]), text=str(q["quote"])) for q in raw["quotes"]]
    refs = list(dict.fromkeys(span.ref for span in spans))
    claims = [ref for ref in refs if ref in allowed and allowed[ref].kind == "CLAIM"]
    return ComposedSentence(
        text=str(raw["text"]),
        claim_ids=[uuid.UUID(ref) for ref in claims],
        evidence_ids=[ref for ref in refs if ref not in claims],
        spans=spans,
    )


def _heading_problem(heading: str) -> str | None:
    if not heading or len(heading) > HEADING_MAX_CHARS:
        return f"is empty or longer than {HEADING_MAX_CHARS} characters"
    if figures_in(heading):
        return "carries a number or formula"
    return free_text_problem(heading)


def _usable_follow_ups(raw: list[Any]) -> list[str]:
    texts = [str(item).strip() for item in raw]
    return [text for text in texts if text and free_text_problem(text) is None][:FOLLOW_UPS_MAX]


def _list(raw: Mapping[str, Any], key: str) -> list[Any]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise _unusable(f"{key} is missing or not a list")
    return value


def _unusable(reason: str) -> ExternalFailure:
    return ExternalFailure(f"the compose reply is unusable: {reason}", service=MODEL_SERVICE)


def _reason(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return ", ".join(sorted({".".join(str(p) for p in e["loc"]) or "sentence" for e in error.errors()}))
    return type(error).__name__
