from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.providers.elevenlabs import HeardWord
from app.schemas.artisan import ArtisanTranscript, TranscriptTurn, TranscriptWord

from .privacy import TranscriptCipher

__all__ = [
    "Located",
    "artisan_turns",
    "located_span",
    "open_transcript",
    "sealed_merge",
    "topic_counts",
    "words_from",
]

MS = 1000


@dataclass(frozen=True)
class Located:
    start_ms: int
    end_ms: int
    precision: str


def open_transcript(cipher: TranscriptCipher, sealed: str | None) -> ArtisanTranscript:
    opened = cipher.open(sealed)
    if not opened:
        return ArtisanTranscript()
    try:
        return ArtisanTranscript.model_validate(opened)
    except ValidationError as error:
        raise InvalidInput(f"The stored artisan transcript breaks its shape: {error}") from None


def sealed_merge(cipher: TranscriptCipher, *turns: TranscriptTurn) -> Callable[[str | None], str]:
    def merge(sealed: str | None) -> str:
        transcript = open_transcript(cipher, sealed)
        kept = list(transcript.turns)
        for turn in turns:
            kept.append(turn.model_copy(update={"ordinal": len(kept)}))
        merged = ArtisanTranscript(turns=kept)
        return cipher.seal(merged.model_dump(mode="json", by_alias=True))

    return merge


def artisan_turns(transcript: ArtisanTranscript) -> list[TranscriptTurn]:
    return [turn for turn in transcript.turns if turn.speaker == "ARTISAN"]


def topic_counts(transcript: ArtisanTranscript) -> dict[str, int]:
    counts: dict[str, int] = {}
    for turn in transcript.turns:
        if turn.speaker == "KALAVIGYAN" and turn.topic is not None:
            counts[turn.topic] = counts.get(turn.topic, 0) + 1
    return counts


def words_from(heard: Sequence[HeardWord], offset_ms: int) -> list[TranscriptWord]:
    return [
        TranscriptWord(text=word.text, start=offset_ms / MS + word.start, end=offset_ms / MS + word.end)
        for word in heard
    ]


def located_span(turn: TranscriptTurn, start: int, end: int) -> Located:
    fallback = Located(turn.start_ms, max(turn.end_ms, turn.start_ms + 1), "TURN")
    if not turn.words:
        return fallback
    covered = _covered_words(turn.text, turn.words, start, end)
    if not covered:
        return fallback
    first, last = covered[0], covered[-1]
    start_ms, end_ms = round(first.start * MS), round(last.end * MS)
    if end_ms <= start_ms:
        return fallback
    return Located(start_ms, end_ms, "WORD")


def _covered_words(text: str, words: Sequence[TranscriptWord], start: int, end: int) -> list[TranscriptWord]:
    cursor = 0
    covered: list[TranscriptWord] = []
    for word in words:
        found = text.find(word.text, cursor)
        if found < 0:
            return []
        cursor = found + len(word.text)
        if found < end and cursor > start:
            covered.append(word)
    return covered
