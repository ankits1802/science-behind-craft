from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.providers.quota import LedgerEntry
from app.research.crafts import CraftRef

from .records import AnswerRecord, SessionRecord

__all__ = [
    "ARTISAN_PURPOSE",
    "ArtisanFacts",
    "ArtisanStore",
    "AudioWrite",
    "ContributionWrite",
    "ConversationRecord",
    "NewConversation",
    "TurnWrite",
]

ARTISAN_PURPOSE = "ARTISAN"


@dataclass(frozen=True, kw_only=True)
class ConversationRecord:
    id: uuid.UUID
    user_id: uuid.UUID
    voice_session_id: uuid.UUID | None
    craft: CraftRef
    craft_id: uuid.UUID
    district: str | None
    language: str
    transport: str
    started_at: datetime
    ended_at: datetime | None = None
    transcript: str | None = None
    topics_asked: tuple[str, ...] = ()
    extraction: str = "PENDING"
    attempts: int = 0
    deleted_at: datetime | None = None
    role: str = ""


@dataclass(frozen=True, kw_only=True)
class ArtisanFacts:
    crafts: tuple[tuple[uuid.UUID, CraftRef], ...] = ()
    consent: tuple[uuid.UUID, str] | None = None
    district: str | None = None

    def craft(self, craft_id: uuid.UUID) -> CraftRef | None:
        return next((ref for held, ref in self.crafts if held == craft_id), None)


@dataclass(frozen=True, kw_only=True)
class NewConversation:
    session: SessionRecord
    conversation_id: uuid.UUID
    craft_id: uuid.UUID
    consent_record_id: uuid.UUID
    consent_version: str
    transcript: str | None = None
    topics_asked: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class AudioWrite:
    turn_id: uuid.UUID
    ordinal: int
    object_key: str
    mime_type: str
    byte_count: int
    duration_ms: int
    start_ms: int


@dataclass(frozen=True, kw_only=True)
class TurnWrite:
    merge: Callable[[str | None], str]
    topics_asked: tuple[str, ...] | None = None
    answer: AnswerRecord | None = None
    seconds: tuple[LedgerEntry, ...] = ()
    audio: AudioWrite | None = None


@dataclass(frozen=True, kw_only=True)
class ContributionWrite:
    turn_id: uuid.UUID
    ordinal: int
    quote: str
    english: str
    english_source: str
    claim_text: str
    discipline: str
    concept_type: str
    concept_name: str
    start_ms: int
    end_ms: int
    precision: str
    screens: tuple[str, ...] = field(default_factory=tuple)


class ArtisanStore(Protocol):
    async def facts(self, user_id: uuid.UUID) -> ArtisanFacts: ...

    async def craft_id(self, slug: str) -> uuid.UUID | None: ...

    async def held_back(self, user_id: uuid.UUID) -> frozenset[str]: ...

    async def start(self, new: NewConversation) -> bool: ...

    async def by_id(self, conversation_id: uuid.UUID) -> ConversationRecord | None: ...

    async def by_voice_session(self, voice_session_id: uuid.UUID) -> ConversationRecord | None: ...

    async def topics_asked_before(self, user_id: uuid.UUID, craft_id: uuid.UUID) -> tuple[str, ...]: ...

    async def save_turn(self, conversation_id: uuid.UUID, write: TurnWrite) -> None: ...

    async def finish(
        self, conversation_id: uuid.UUID, now: datetime, *, spoke: bool
    ) -> ConversationRecord | None: ...

    async def claim_extraction(
        self, conversation_id: uuid.UUID, now: datetime
    ) -> ConversationRecord | None: ...

    async def save_extraction(
        self, conversation_id: uuid.UUID, status: str, items: Sequence[ContributionWrite], now: datetime
    ) -> None: ...

    async def due_extractions(self, limit: int, *, max_attempts: int) -> list[uuid.UUID]: ...

    async def unfinished(self, now: datetime, limit: int) -> list[uuid.UUID]: ...
