import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from app.research.crafts import CraftRef
from app.research.testimony import RECORDING_NOTICE_VERSION
from app.schemas.artisan import ArtisanTranscript, TranscriptTurn, TranscriptWord
from app.voice.artisan_records import (
    ArtisanFacts,
    ContributionWrite,
    ConversationRecord,
    NewConversation,
    TurnWrite,
)
from app.voice.privacy import TranscriptCipher

from .fakes import CRAFT, START, USER_ID, cipher

CRAFT_ID = uuid.UUID("11111111-2222-4333-8444-555555555555")
OTHER_CRAFT = CraftRef(slug="kutch-bandhani", name="Bandhani", path="/crafts/kutch-bandhani")
OTHER_CRAFT_ID = uuid.UUID("11111111-2222-4333-8444-666666666666")
CONSENT_ID = uuid.UUID("22222222-3333-4444-8555-666666666666")
CONVERSATION_ID = uuid.UUID("33333333-4444-4555-8666-777777777777")
TERMS = frozenset({"ismail", "khatri"})


def artisan_user(**changes: Any) -> Any:
    @dataclass
    class Artisan:
        id: uuid.UUID = USER_ID
        role: str = "ARTISAN"
        emailVerifiedAt: datetime | None = START
        name: str = "Ismail Khatri"

    return replace(Artisan(), **changes)


def facts(
    *, consent: bool = True, crafts: Sequence[tuple[uuid.UUID, CraftRef]] | None = None
) -> ArtisanFacts:
    return ArtisanFacts(
        crafts=tuple(crafts if crafts is not None else [(CRAFT_ID, CRAFT)]),
        consent=(CONSENT_ID, RECORDING_NOTICE_VERSION) if consent else None,
        district="Kachchh",
    )


def artisan_turn(ordinal: int, text: str, **changes: Any) -> TranscriptTurn:
    return TranscriptTurn(
        id=uuid.UUID(int=1000 + ordinal),
        ordinal=ordinal,
        speaker="ARTISAN",
        text=text,
        start_ms=changes.pop("start_ms", ordinal * 10_000),
        end_ms=changes.pop("end_ms", ordinal * 10_000 + 8_000),
        **changes,
    )


def kalavigyan_turn(ordinal: int, text: str, topic: str | None = "PROCESS", **changes: Any) -> TranscriptTurn:
    return TranscriptTurn(
        id=uuid.UUID(int=2000 + ordinal),
        ordinal=ordinal,
        speaker="KALAVIGYAN",
        text=text,
        english=changes.pop("english", text),
        topic=topic,
        start_ms=ordinal * 10_000,
        end_ms=ordinal * 10_000 + 2_000,
        **changes,
    )


def timed_words(text: str, start: float) -> list[TranscriptWord]:
    words, at = [], start
    for word in text.split():
        words.append(TranscriptWord(text=word, start=at, end=at + 0.4))
        at += 0.5
    return words


def sealed(*turns: TranscriptTurn, key: TranscriptCipher | None = None) -> str:
    transcript = ArtisanTranscript(turns=list(turns))
    return (key or cipher()).seal(transcript.model_dump(mode="json", by_alias=True))


def conversation(**changes: Any) -> ConversationRecord:
    record = ConversationRecord(
        id=CONVERSATION_ID,
        user_id=USER_ID,
        voice_session_id=None,
        craft=CRAFT,
        craft_id=CRAFT_ID,
        district="Kachchh",
        language="en",
        transport="RELAY",
        started_at=START,
        role="ARTISAN",
    )
    return replace(record, **changes)


@dataclass
class MemoryArtisanStore:
    known: ArtisanFacts = field(default_factory=facts)
    slugs: dict[str, uuid.UUID] = field(
        default_factory=lambda: {CRAFT.slug: CRAFT_ID, OTHER_CRAFT.slug: OTHER_CRAFT_ID}
    )
    conversations: dict[uuid.UUID, ConversationRecord] = field(default_factory=dict)
    earlier_topics: tuple[str, ...] = ()
    terms: frozenset[str] = TERMS
    audio: list[Any] = field(default_factory=list)
    answers: list[Any] = field(default_factory=list)
    contributions: list[ContributionWrite] = field(default_factory=list)
    started: list[NewConversation] = field(default_factory=list)
    voice: Any = None

    async def facts(self, user_id: uuid.UUID) -> ArtisanFacts:
        return self.known

    async def craft_id(self, slug: str) -> uuid.UUID | None:
        return self.slugs.get(slug)

    async def held_back(self, user_id: uuid.UUID) -> frozenset[str]:
        return self.terms

    async def start(self, new: NewConversation) -> bool:
        self.started.append(new)
        record = new.session
        if self.voice is not None and not await self.voice.create(record):
            return False
        self.conversations[new.conversation_id] = conversation(
            id=new.conversation_id,
            voice_session_id=record.id,
            craft=record.craft or CRAFT,
            craft_id=new.craft_id,
            language=record.language,
            transport=record.transport,
            started_at=record.started_at,
            transcript=new.transcript,
            topics_asked=new.topics_asked,
        )
        return True

    async def by_id(self, conversation_id: uuid.UUID) -> ConversationRecord | None:
        return self.conversations.get(conversation_id)

    async def by_voice_session(self, voice_session_id: uuid.UUID) -> ConversationRecord | None:
        return next((c for c in self.conversations.values() if c.voice_session_id == voice_session_id), None)

    async def topics_asked_before(self, user_id: uuid.UUID, craft_id: uuid.UUID) -> tuple[str, ...]:
        return self.earlier_topics

    async def save_turn(self, conversation_id: uuid.UUID, write: TurnWrite) -> None:
        record = self.conversations[conversation_id]
        topics = write.topics_asked if write.topics_asked is not None else record.topics_asked
        self.conversations[conversation_id] = replace(
            record, transcript=write.merge(record.transcript), topics_asked=topics
        )
        if write.audio is not None:
            self.audio.append(write.audio)
        if write.answer is not None:
            self.answers.append(write.answer)

    async def finish(
        self, conversation_id: uuid.UUID, now: datetime, *, spoke: bool
    ) -> ConversationRecord | None:
        record = self.conversations[conversation_id]
        if record.ended_at is None:
            record = replace(record, ended_at=now, extraction="PENDING" if spoke else "NONE")
            self.conversations[conversation_id] = record
        return record

    async def claim_extraction(self, conversation_id: uuid.UUID, now: datetime) -> ConversationRecord | None:
        record = self.conversations.get(conversation_id)
        if record is None or record.extraction not in ("PENDING", "WAITING", "FAILED"):
            return None
        record = replace(record, extraction="RUNNING", attempts=record.attempts + 1)
        self.conversations[conversation_id] = record
        return record

    async def save_extraction(
        self, conversation_id: uuid.UUID, status: str, items: Sequence[ContributionWrite], now: datetime
    ) -> None:
        self.contributions.extend(items)
        self.conversations[conversation_id] = replace(self.conversations[conversation_id], extraction=status)

    async def due_extractions(self, limit: int, *, max_attempts: int) -> list[uuid.UUID]:
        return [
            c.id
            for c in self.conversations.values()
            if c.ended_at
            and c.extraction in ("PENDING", "WAITING", "FAILED")
            and (c.extraction == "PENDING" or c.attempts < max_attempts)
        ][:limit]

    async def unfinished(self, now: datetime, limit: int) -> list[uuid.UUID]:
        return []
