from __future__ import annotations

import uuid
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from typing import Any

from app.models import (
    ArtisanContribution,
    ArtisanConversation,
    ArtisanConversationAudio,
    ArtisanProfile,
    Craft,
)
from app.services.object_store import PresignedGet

USER = uuid.UUID("2b3c4d5e-6f70-4a81-92a3-b4c5d6e7f809")
OTHER_USER = uuid.UUID("4c5d6e7f-8091-4a2b-b3c4-d5e6f708192a")
CRAFT = uuid.UUID("8e9f0a1b-2c3d-4e5f-8a6b-7c8d9e0f1a2b")
CONVERSATION = uuid.UUID("9b2c4d6e-8f0a-4b1c-9d2e-3f4a5b6c7d8e")
TURN = uuid.UUID("5a6b7c8d-9e0f-4a1b-8c2d-3e4f5a6b7c8d")
BEFORE_TURN = uuid.UUID("7b8c9d0e-1f2a-4b3c-8d4e-5f6a7b8c9d0e")
PENDING_ID = uuid.UUID("3f1e8b7a-2c4d-4e5f-9a1b-0c2d3e4f5a6b")
APPROVED_ID = uuid.UUID("1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d")
WITHDRAWN_ID = uuid.UUID("6d7e8f90-a1b2-4c3d-8e4f-5a6b7c8d9e0f")
REVIEWER = uuid.UUID("0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d")
DISTRICT_LGD = 468
STATE_LGD = 24
QUOTE = "फिटकरी के बाद हम कपड़े को बहते पानी में धोते हैं"
TURN_TEXT = "हाँ। फिटकरी के बाद हम कपड़े को बहते पानी में धोते हैं, फिर धूप में सुखाते हैं।"
ENGLISH = "After the alum we wash the cloth in running water"
CLAIM = "After the alum bath the printed cloth is washed in running water."
AUDIO_KEY = (
    "media/2b3c4d5e-6f70-4a81-92a3-b4c5d6e7f809/0f1e2d3c4b5a69788796a5b4c3d2e1f0/"
    "KalaVigyan_Artisan-Conversation_2026-11-18_1100_Kachchh_Ajrakh-Printing_Recording_T03.webm"
)
AUDIO_URL = f"https://kalavigyan-media.s3.ap-south-1.amazonaws.com/{AUDIO_KEY}?X-Amz-Expires=900"


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 18, hour, minute, tzinfo=UTC)


class FakeResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def first(self) -> Any:
        return self._value

    def all(self) -> list[Any]:
        return list(self._value)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._value)


class FakeSession:
    def __init__(
        self,
        rows: Mapping[tuple[type, Any], Any] | None = None,
        *,
        scalars: list[Any] | None = None,
        executed: list[Any] | None = None,
    ) -> None:
        self.rows = dict(rows or {})
        self.scalars_left = list(scalars or [])
        self.executed_left = list(executed or [])
        self.rolled_back = False
        self.committed = False

    async def get(self, model: type, key: Any, **_options: Any) -> Any:
        return self.rows.get((model, key))

    async def scalar(self, _statement: Any) -> Any:
        return self.scalars_left.pop(0) if self.scalars_left else None

    async def execute(self, _statement: Any) -> FakeResult:
        return FakeResult(self.executed_left.pop(0) if self.executed_left else [])

    async def rollback(self) -> None:
        self.rolled_back = True

    async def commit(self) -> None:
        self.committed = True


class FakeLinks:
    def presigned_get(self, key: str, *, disposition: str, seconds: int, now: datetime) -> PresignedGet:
        assert key == AUDIO_KEY and seconds == 900 and disposition.startswith("inline;")
        return PresignedGet(url=AUDIO_URL, expires_at=at(7, 15))


def craft() -> Craft:
    return Craft(id=CRAFT, slug="kutch-ajrakh", name="Ajrakh Printing")


def conversation(**changes: Any) -> ArtisanConversation:
    fields: dict[str, Any] = {
        "id": CONVERSATION,
        "userId": USER,
        "craftId": CRAFT,
        "language": "hi",
        "transport": "RELAY",
        "consentVersion": "2026-11-18",
        "startedAt": at(5, 30),
        "endedAt": at(5, 50),
        "extractionStatus": "DONE",
    }
    return ArtisanConversation(**(fields | changes))


def profile(**changes: Any) -> ArtisanProfile:
    fields: dict[str, Any] = {
        "userId": USER,
        "districtLgd": DISTRICT_LGD,
        "spokenLanguage": "hi",
        "creditMode": "CRAFT_AND_DISTRICT",
        "creditName": None,
        "creditShortName": None,
        "adultConfirmedAt": at(5),
        "completedAt": at(5),
    }
    return ArtisanProfile(**(fields | changes))


def contribution(**changes: Any) -> ArtisanContribution:
    fields: dict[str, Any] = {
        "id": PENDING_ID,
        "conversationId": CONVERSATION,
        "userId": USER,
        "craftId": CRAFT,
        "turnId": TURN,
        "ordinal": 3,
        "status": "PENDING",
        "quote": QUOTE,
        "quoteLanguage": "hi",
        "english": ENGLISH,
        "englishSource": "MACHINE",
        "claimText": CLAIM,
        "discipline": "PROCESS",
        "conceptType": "PROCESS_STAGE",
        "conceptName": "Washing in running water",
        "startMs": 65_000,
        "endMs": 72_000,
        "locatorPrecision": "WORD",
        "screens": [],
        "corroboratingClaimIds": [],
        "version": 2,
        "createdAt": at(6, 2),
    }
    return ArtisanContribution(**(fields | changes))


def audio() -> ArtisanConversationAudio:
    return ArtisanConversationAudio(
        conversationId=CONVERSATION,
        turnId=TURN,
        ordinal=3,
        objectKey=AUDIO_KEY,
        mimeType="audio/webm",
        bytes=48_000,
        durationMs=12_000,
        startMs=63_000,
    )


def turns() -> dict[str, dict[str, Any]]:
    return {
        str(BEFORE_TURN): {
            "id": str(BEFORE_TURN),
            "ordinal": 2,
            "speaker": "KALAVIGYAN",
            "text": "फिटकरी के बाद आप कपड़े के साथ क्या करते हैं?",
            "english": "What do you do with the cloth after the alum?",
            "answerId": None,
            "startMs": 55_000,
            "endMs": 62_000,
        },
        str(TURN): {
            "id": str(TURN),
            "ordinal": 3,
            "speaker": "ARTISAN",
            "text": TURN_TEXT,
            "english": None,
            "answerId": None,
            "startMs": 63_000,
            "endMs": 75_000,
        },
    }


def district_row() -> tuple[int, str, int, str]:
    return (DISTRICT_LGD, "Kachchh", STATE_LGD, "Gujarat")


def session_for(item: ArtisanContribution, **options: Any) -> FakeSession:
    rows = {
        (Craft, CRAFT): craft(),
        (ArtisanConversation, CONVERSATION): conversation(),
        (ArtisanProfile, USER): profile(),
        (ArtisanContribution, item.id): item,
    }
    return FakeSession(rows, **options)
