from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.schemas.voice import MAX_SPOKEN_WORDS

from .phrases import SOURCE_WORDS

__all__ = [
    "LABEL_MAX_WORDS",
    "SpokenReply",
    "spoken_label",
    "spoken_reply",
    "word_count",
]

LABEL_MAX_WORDS = 5
LABEL_CUT = re.compile(r" \(|, | - | – |: |; ")
GI_ISSUE = re.compile(r"\bNo\.\s*(\d+)")
AUTHORED_KINDS = frozenset({"PAPER", "BOOK", "BOOK_CHAPTER"})


@dataclass(frozen=True)
class SpokenReply:
    sentences: tuple[dict[str, Any], ...]
    parts: tuple[str, ...]

    @property
    def text(self) -> str:
        return "".join(self.parts)


def word_count(text: str) -> int:
    return len(text.split())


def spoken_label(source: Mapping[str, Any]) -> str:
    title = str(source.get("title") or "").strip()
    issue = GI_ISSUE.search(title)
    if source.get("kind") == "GI_JOURNAL" and issue:
        return f"GI Journal {issue.group(1)}"
    authors = [str(a).strip() for a in source.get("authors") or [] if str(a).strip()]
    if source.get("kind") in AUTHORED_KINDS and authors and source.get("year"):
        return f"{authors[0].split()[-1].strip(',.;')} {source['year']}"
    head = LABEL_CUT.split(title, maxsplit=1)[0].strip().rstrip(".")
    return " ".join(head.split()[:LABEL_MAX_WORDS])


def spoken_reply(
    sentences: Sequence[dict[str, Any]], sources: Mapping[str, Mapping[str, Any]], *, language: str
) -> SpokenReply:
    kept: list[dict[str, Any]] = []
    labels: list[str] = []
    for sentence in sentences:
        with_this = _labels_after(labels, sentence, sources)
        parts = _parts([*(s["text"] for s in kept), sentence["text"]], with_this, language)
        if word_count("".join(parts)) <= MAX_SPOKEN_WORDS:
            kept.append(sentence)
            labels = with_this
    return SpokenReply(
        sentences=tuple(kept), parts=tuple(_parts([s["text"] for s in kept], labels, language))
    )


def _labels_after(
    labels: list[str], sentence: Mapping[str, Any], sources: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    found = list(labels)
    for citation in sentence["citations"]:
        label = spoken_label(sources[citation["sourceId"]])
        if label and label not in found:
            found.append(label)
    return found


def _parts(texts: Sequence[str], labels: Sequence[str], language: str) -> list[str]:
    if not texts:
        return []
    parts = [texts[0], *(f" {text}" for text in texts[1:])]
    if labels:
        singular, plural = SOURCE_WORDS[language]
        word = singular if len(labels) == 1 else plural
        parts.append(f" {word}: {'; '.join(labels)}.")
    return parts
