from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from pydantic import TypeAdapter

from app.core.errors import InvalidInput
from app.schemas.voice import TRANSCRIPT_RETENTION_DAYS, VoiceTranscript

from .privacy import TranscriptCipher
from .records import SessionRecord
from .turns import SpokenTurn

__all__ = [
    "TRANSCRIPT_VERSION",
    "SavedTurn",
    "StoredTranscript",
    "retention_until",
    "stored_transcript",
    "transcript_view",
    "turn_merge",
]

TRANSCRIPT_VERSION = 1
TRANSCRIPT_SHAPE = TypeAdapter(VoiceTranscript)


class StoredTranscript:
    def __init__(self, turns: list[dict[str, Any]], sources: dict[str, dict[str, Any]]) -> None:
        self.turns = turns
        self.sources = sources

    @property
    def next_ordinal(self) -> int:
        return len(self.turns) + 1

    def cited_source_ids(self) -> set[str]:
        return {c["sourceId"] for turn in self.turns for s in turn["sentences"] for c in s["citations"]}

    def spoken_of(self, turn_id: uuid.UUID) -> str | None:
        return next((turn["spoken"] for turn in self.turns if turn["turnId"] == str(turn_id)), None)

    def with_turn(self, turn: SpokenTurn) -> StoredTranscript:
        sources = dict(self.sources)
        sources.update({source["id"]: source for source in turn.sources})
        return StoredTranscript([*self.turns, turn.view()], sources)

    def sealed(self, cipher: TranscriptCipher) -> str:
        return cipher.seal({"version": TRANSCRIPT_VERSION, "turns": self.turns, "sources": self.sources})


def stored_transcript(cipher: TranscriptCipher, sealed: str | None) -> StoredTranscript:
    opened = cipher.open(sealed)
    if not opened:
        return StoredTranscript([], {})
    if opened.get("version") != TRANSCRIPT_VERSION:
        raise InvalidInput(f"Voice transcript version {opened.get('version')!r} is not {TRANSCRIPT_VERSION}")
    return StoredTranscript(list(opened["turns"]), dict(opened["sources"]))


def retention_until(ended_or_hard_end: datetime) -> datetime:
    return ended_or_hard_end + timedelta(days=TRANSCRIPT_RETENTION_DAYS)


def transcript_view(record: SessionRecord, stored: StoredTranscript) -> dict[str, Any]:
    cited = dict.fromkeys(
        c["sourceId"] for turn in stored.turns for s in turn["sentences"] for c in s["citations"]
    )
    payload = {
        "voiceSessionId": str(record.id),
        "language": record.language,
        "mode": record.mode,
        "craft": record.craft.model_dump(mode="json", by_alias=True) if record.craft else None,
        "retentionUntil": (record.retention_until or retention_until(record.hard_end)).isoformat(),
        "turns": stored.turns,
        "sources": [stored.sources[source_id] for source_id in cited],
    }
    return TRANSCRIPT_SHAPE.dump_python(TRANSCRIPT_SHAPE.validate_python(payload), mode="json", by_alias=True)


@dataclass
class SavedTurn:
    turn: SpokenTurn | None = None
    earlier_sources: set[str] = field(default_factory=set)


def turn_merge(cipher: TranscriptCipher, turn: SpokenTurn) -> tuple[Callable[[str | None], str], SavedTurn]:
    saved = SavedTurn()

    def merge(current: str | None) -> str:
        stored = stored_transcript(cipher, current)
        saved.turn = turn.renumbered(stored.next_ordinal)
        saved.earlier_sources = stored.cited_source_ids()
        return stored.with_turn(saved.turn).sealed(cipher)

    return merge, saved
