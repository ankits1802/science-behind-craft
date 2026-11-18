from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArtisanContribution, ArtisanConversation, ArtisanConversationAudio
from app.research.testimony import TESTIMONY_RETENTION_DAYS

__all__ = [
    "RETENTION",
    "UNFINISHED_EXTRACTION",
    "AudioObjects",
    "purge_conversation",
    "purge_due",
    "settle_retention",
]

RETENTION = timedelta(days=TESTIMONY_RETENTION_DAYS)
UNFINISHED_EXTRACTION = ("PENDING", "RUNNING", "WAITING", "FAILED")
KEPT_STATUSES = ("PENDING", "APPROVED")
PURGE_BATCH = 200


class AudioObjects(Protocol):
    async def delete(self, key: str) -> None: ...


async def settle_retention(
    session: AsyncSession, conversation_id: uuid.UUID, *, now: datetime, at_once: bool
) -> datetime | None:
    conversation = await session.get(ArtisanConversation, conversation_id, with_for_update=True)
    if conversation is None:
        return None
    if conversation.endedAt is None or conversation.extractionStatus in UNFINISHED_EXTRACTION:
        conversation.retentionUntil = None
        return None
    kept = await session.scalar(
        select(ArtisanContribution.id)
        .where(
            ArtisanContribution.conversationId == conversation_id,
            ArtisanContribution.status.in_(KEPT_STATUSES),
        )
        .limit(1)
    )
    conversation.retentionUntil = None if kept is not None else (now if at_once else now + RETENTION)
    return conversation.retentionUntil


async def purge_conversation(session: AsyncSession, objects: AudioObjects, conversation_id: uuid.UUID) -> int:
    keys = list(
        await session.scalars(
            select(ArtisanConversationAudio.objectKey).where(
                ArtisanConversationAudio.conversationId == conversation_id
            )
        )
    )
    for key in keys:
        await objects.delete(key)
    await session.execute(
        delete(ArtisanConversationAudio).where(ArtisanConversationAudio.conversationId == conversation_id)
    )
    await session.execute(
        update(ArtisanConversation)
        .where(ArtisanConversation.id == conversation_id)
        .values(transcriptEnc=None)
    )
    return len(keys)


async def purge_due(session: AsyncSession, objects: AudioObjects, *, now: datetime) -> int:
    due = list(
        await session.scalars(
            select(ArtisanConversation.id)
            .where(ArtisanConversation.retentionUntil <= now)
            .where(
                ArtisanConversation.transcriptEnc.is_not(None)
                | ArtisanConversation.id.in_(select(ArtisanConversationAudio.conversationId))
            )
            .limit(PURGE_BATCH)
        )
    )
    for conversation_id in due:
        await purge_conversation(session, objects, conversation_id)
    return len(due)
