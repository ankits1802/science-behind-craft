from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.errors import AppError
from app.data.craft_text import script_of
from app.research.translation import (
    TRANSLATION_ITEM_MAX_CHARS,
    TranslationItem,
    TranslationRequest,
    Translator,
)
from app.research.vocabulary import CANONICAL_LANGUAGE

from .answer_events import StreamEvent

__all__ = [
    "ENGLISH_SCRIPTS",
    "AnswerTranslation",
    "Segment",
    "TranslationCache",
    "english_question",
    "needs_english_rendering",
    "translate_segments",
    "translated_composed_events",
    "translated_sentences",
    "translated_stored_events",
]

logger = logging.getLogger(__name__)

ENGLISH_SCRIPTS = frozenset({"Latn", "Zyyy"})
SENTENCE_EVENTS = frozenset({"sentence", "open_question"})
QUESTION_KEY = "question"


class TranslationCache(Protocol):
    async def known(self, language: str, texts: Mapping[uuid.UUID, str]) -> dict[uuid.UUID, str]: ...

    async def remember(self, language: str, entries: Mapping[uuid.UUID, tuple[str, str]]) -> None: ...


@dataclass(frozen=True)
class AnswerTranslation:
    translator: Translator
    cache: TranslationCache


@dataclass(frozen=True)
class Segment:
    key: str
    text: str
    claim_id: uuid.UUID | None = None


def needs_english_rendering(question: str) -> bool:
    return script_of(question) not in ENGLISH_SCRIPTS


async def english_question(question: str, translation: AnswerTranslation) -> str:
    if not needs_english_rendering(question):
        return question
    rendered = await _translated(
        [Segment(QUESTION_KEY, question)], CANONICAL_LANGUAGE, translation.translator
    )
    return rendered.get(QUESTION_KEY, question)


async def translated_stored_events(
    events: Sequence[StreamEvent],
    *,
    language: str,
    translation: AnswerTranslation,
    claim_texts: Mapping[uuid.UUID, str],
) -> list[StreamEvent]:
    segments = _sentence_segments(_sentences_of(events), claim_texts)
    found = await translate_segments(segments, language=language, translation=translation)
    return [_applied(name, payload, found) for name, payload in events]


async def translated_composed_events(
    events: Sequence[StreamEvent],
    *,
    language: str,
    translation: AnswerTranslation,
    claim_texts: Mapping[uuid.UUID, str],
) -> list[StreamEvent]:
    segments = [*_sentence_segments(_sentences_of(events), claim_texts), *_label_segments(events)]
    found = await translate_segments(segments, language=language, translation=translation)
    return [_applied(name, payload, found) for name, payload in events]


async def translated_sentences(
    sentences: Sequence[Mapping[str, Any]],
    *,
    language: str,
    translation: AnswerTranslation,
    claim_texts: Mapping[uuid.UUID, str],
) -> list[dict[str, Any]]:
    found = await translate_segments(
        _sentence_segments(sentences, claim_texts), language=language, translation=translation
    )
    return [_translated_sentence(sentence, found) for sentence in sentences]


async def translate_segments(
    segments: Sequence[Segment], *, language: str, translation: AnswerTranslation
) -> dict[str, str]:
    if language == CANONICAL_LANGUAGE or not segments:
        return {}
    cacheable = {segment.claim_id: segment.text for segment in segments if segment.claim_id is not None}
    cached = await translation.cache.known(language, cacheable) if cacheable else {}
    found = {s.key: cached[s.claim_id] for s in segments if s.claim_id is not None and s.claim_id in cached}
    pending = [segment for segment in segments if segment.key not in found]
    if not pending:
        return found
    fresh = await _translated(pending, language, translation.translator)
    learned = {
        s.claim_id: (s.text, fresh[s.key]) for s in pending if s.claim_id is not None and s.key in fresh
    }
    if learned:
        await translation.cache.remember(language, learned)
    return found | fresh


async def _translated(segments: Sequence[Segment], language: str, translator: Translator) -> dict[str, str]:
    items = [
        TranslationItem(key=segment.key, text=segment.text)
        for segment in segments
        if len(segment.text) <= TRANSLATION_ITEM_MAX_CHARS
    ]
    if not items:
        return {}
    try:
        return await translator.translate(TranslationRequest(language=language, items=items))
    except AppError as error:
        logger.warning("translation into %s failed, the original stays: %s", language, error)
        return {}


def _sentences_of(events: Sequence[StreamEvent]) -> list[Mapping[str, Any]]:
    return [payload["sentence"] for name, payload in events if name in SENTENCE_EVENTS]


def _sentence_segments(
    sentences: Sequence[Mapping[str, Any]], claim_texts: Mapping[uuid.UUID, str]
) -> list[Segment]:
    return [Segment(s["id"], s["text"], _claim_of(s, claim_texts)) for s in sentences]


def _claim_of(sentence: Mapping[str, Any], claim_texts: Mapping[uuid.UUID, str]) -> uuid.UUID | None:
    claims = {citation["claimId"] for citation in sentence["citations"]}
    if len(claims) != 1:
        return None
    claim_id = uuid.UUID(claims.pop())
    return claim_id if claim_texts.get(claim_id) == sentence["text"] else None


def _label_segments(events: Sequence[StreamEvent]) -> list[Segment]:
    segments: list[Segment] = []
    for name, payload in events:
        if name == "section":
            segments.append(Segment(_heading_key(payload["id"]), payload["heading"]))
        elif name == "follow_ups":
            segments += [Segment(_follow_up_key(n), item) for n, item in enumerate(payload["items"])]
    return segments


def _applied(name: str, payload: dict[str, Any], found: Mapping[str, str]) -> StreamEvent:
    if name in SENTENCE_EVENTS:
        return name, {**payload, "sentence": _translated_sentence(payload["sentence"], found)}
    if name == "section" and _heading_key(payload["id"]) in found:
        return name, {
            **payload,
            "heading": found[_heading_key(payload["id"])],
            "original": payload["heading"],
        }
    if name == "follow_ups":
        items = [found.get(_follow_up_key(n), item) for n, item in enumerate(payload["items"])]
        return name, {**payload, "items": items}
    return name, payload


def _translated_sentence(sentence: Mapping[str, Any], found: Mapping[str, str]) -> dict[str, Any]:
    text = found.get(sentence["id"])
    if text is None:
        return dict(sentence)
    return {**sentence, "text": text, "translated": True, "original": sentence["text"]}


def _heading_key(section_id: str) -> str:
    return f"heading:{section_id}"


def _follow_up_key(index: int) -> str:
    return f"follow-up:{index}"
