from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    AdminDistrict,
    ArtisanContribution,
    ArtisanConversation,
    ArtisanConversationAudio,
    ArtisanProfile,
    Conversation,
    Craft,
    User,
    VoiceSession,
)
from app.providers.quota import record_units
from app.research.crafts import CraftRef
from app.services import knowledge_view
from app.services.conversation_retention import settle_retention
from app.services.reader_profiles import (
    artisan_crafts,
    artisan_profile,
    district_names,
    held_back_name_terms,
    recording_consent,
)

from .artisan_records import (
    ArtisanFacts,
    AudioWrite,
    ContributionWrite,
    ConversationRecord,
    NewConversation,
    TurnWrite,
)
from .store import answer_row, session_row

__all__ = ["CLAIMABLE_EXTRACTION", "SqlArtisanStore"]

CLAIMABLE_EXTRACTION = ("PENDING", "WAITING", "FAILED")
LIVE_INDEX = "VoiceSession_one_live_per_user_key"


class SqlArtisanStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def facts(self, user_id: uuid.UUID) -> ArtisanFacts:
        async with self._sessions() as session:
            crafts = await artisan_crafts(session, user_id)
            consent = await recording_consent(session, user_id)
            profile = await artisan_profile(session, user_id)
            district = await district_names(session, profile.districtLgd) if profile else None
        return ArtisanFacts(
            crafts=tuple(
                (row.craft_id, CraftRef(slug=row.slug, name=row.name, path=f"/crafts/{row.slug}"))
                for row in crafts
            ),
            consent=None if consent is None else (consent.id, consent.noticeVersion),
            district=district.name if district else None,
        )

    async def craft_id(self, slug: str) -> uuid.UUID | None:
        async with self._sessions() as session:
            craft = await knowledge_view.resolve_craft(session, slug)
        return None if craft is None else craft.id

    async def held_back(self, user_id: uuid.UUID) -> frozenset[str]:
        async with self._sessions() as session:
            return await held_back_name_terms(session, user_id)

    async def start(self, new: NewConversation) -> bool:
        record = new.session
        async with self._sessions() as session:
            session.add(
                Conversation(
                    id=record.chat_id,
                    userId=record.user_id,
                    craftId=new.craft_id,
                    mode=record.mode,
                    channel="VOICE",
                    language=record.language,
                )
            )
            session.add(session_row(record, new.craft_id))
            session.add(_conversation_row(new))
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                if LIVE_INDEX not in str(error.orig):
                    raise
                return False
        return True

    async def by_id(self, conversation_id: uuid.UUID) -> ConversationRecord | None:
        return await self._one(ArtisanConversation.id == conversation_id)

    async def by_voice_session(self, voice_session_id: uuid.UUID) -> ConversationRecord | None:
        return await self._one(ArtisanConversation.voiceSessionId == voice_session_id)

    async def topics_asked_before(self, user_id: uuid.UUID, craft_id: uuid.UUID) -> tuple[str, ...]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(func.unnest(ArtisanConversation.topicsAsked)).where(
                    ArtisanConversation.userId == user_id,
                    ArtisanConversation.craftId == craft_id,
                    ArtisanConversation.deletedAt.is_(None),
                )
            )
            return tuple(dict.fromkeys(rows))

    async def save_turn(self, conversation_id: uuid.UUID, write: TurnWrite) -> None:
        async with self._sessions() as session:
            row = await session.get(ArtisanConversation, conversation_id, with_for_update=True)
            if row is None or row.voiceSessionId is None:
                raise LookupError(f"Artisan conversation {conversation_id} is gone")
            voice = await session.get(VoiceSession, row.voiceSessionId, with_for_update=True)
            if voice is None:
                raise LookupError(f"Voice session {row.voiceSessionId} is gone")
            row.transcriptEnc = write.merge(row.transcriptEnc)
            if write.topics_asked is not None:
                row.topicsAsked = list(write.topics_asked)
            if write.answer is not None:
                session.add(await answer_row(session, voice, write.answer))
            for entry in write.seconds:
                await _add_seconds(session, voice, entry)
            if write.audio is not None:
                session.add(_audio_row(conversation_id, write.audio))
            await session.commit()

    async def finish(
        self, conversation_id: uuid.UUID, now: datetime, *, spoke: bool
    ) -> ConversationRecord | None:
        async with self._sessions() as session:
            row = await session.get(ArtisanConversation, conversation_id, with_for_update=True)
            if row is None:
                return None
            if row.endedAt is None:
                row.endedAt = now
                row.extractionStatus = "PENDING" if spoke else "NONE"
                await session.flush()
                if not spoke:
                    await settle_retention(session, conversation_id, now=now, at_once=False)
            await session.commit()
        return await self.by_id(conversation_id)

    async def claim_extraction(self, conversation_id: uuid.UUID, now: datetime) -> ConversationRecord | None:
        async with self._sessions() as session:
            claimed = await session.scalar(
                update(ArtisanConversation)
                .where(
                    ArtisanConversation.id == conversation_id,
                    ArtisanConversation.endedAt.is_not(None),
                    ArtisanConversation.deletedAt.is_(None),
                    ArtisanConversation.extractionStatus.in_(CLAIMABLE_EXTRACTION),
                )
                .values(
                    extractionStatus="RUNNING",
                    extractionAttempts=ArtisanConversation.extractionAttempts + 1,
                    updatedAt=now,
                )
                .returning(ArtisanConversation.id)
            )
            await session.commit()
        return None if claimed is None else await self.by_id(conversation_id)

    async def save_extraction(
        self, conversation_id: uuid.UUID, status: str, items: Sequence[ContributionWrite], now: datetime
    ) -> None:
        async with self._sessions() as session:
            row = await session.get(ArtisanConversation, conversation_id, with_for_update=True)
            if row is None or row.deletedAt is not None:
                return
            for item in items:
                session.add(_contribution_row(row, item, now))
            row.extractionStatus = status
            if status in ("DONE", "NONE"):
                row.extractedAt = now
            await session.flush()
            await settle_retention(session, conversation_id, now=now, at_once=False)
            await session.commit()

    async def due_extractions(self, limit: int, *, max_attempts: int) -> list[uuid.UUID]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(ArtisanConversation.id)
                .where(
                    ArtisanConversation.endedAt.is_not(None),
                    ArtisanConversation.deletedAt.is_(None),
                    ArtisanConversation.extractionStatus.in_(CLAIMABLE_EXTRACTION),
                    or_(
                        ArtisanConversation.extractionStatus == "PENDING",
                        ArtisanConversation.extractionAttempts < max_attempts,
                    ),
                )
                .order_by(ArtisanConversation.endedAt)
                .limit(limit)
            )
            return list(rows)

    async def unfinished(self, now: datetime, limit: int) -> list[uuid.UUID]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(ArtisanConversation.id)
                .join(VoiceSession, VoiceSession.id == ArtisanConversation.voiceSessionId)
                .where(ArtisanConversation.endedAt.is_(None), VoiceSession.endedAt.is_not(None))
                .limit(limit)
            )
            return list(rows)

    async def _one(self, condition: Any) -> ConversationRecord | None:
        query = (
            select(ArtisanConversation, Craft.slug, Craft.name, AdminDistrict.name, User.role)
            .join(Craft, Craft.id == ArtisanConversation.craftId)
            .join(User, User.id == ArtisanConversation.userId)
            .outerjoin(ArtisanProfile, ArtisanProfile.userId == ArtisanConversation.userId)
            .outerjoin(AdminDistrict, AdminDistrict.lgd == ArtisanProfile.districtLgd)
            .where(condition)
            .limit(1)
        )
        async with self._sessions() as session:
            found = (await session.execute(query)).first()
        if found is None:
            return None
        row, slug, name, district, role = found
        return _record(row, CraftRef(slug=slug, name=name, path=f"/crafts/{slug}"), district, role)


def _conversation_row(new: NewConversation) -> ArtisanConversation:
    record = new.session
    return ArtisanConversation(
        id=new.conversation_id,
        userId=record.user_id,
        voiceSessionId=record.id,
        craftId=new.craft_id,
        language=record.language,
        transport=record.transport,
        consentRecordId=new.consent_record_id,
        consentVersion=new.consent_version,
        startedAt=record.started_at,
        transcriptEnc=new.transcript,
        topicsAsked=list(new.topics_asked),
    )


def _audio_row(conversation_id: uuid.UUID, audio: AudioWrite) -> ArtisanConversationAudio:
    return ArtisanConversationAudio(
        conversationId=conversation_id,
        turnId=audio.turn_id,
        ordinal=audio.ordinal,
        objectKey=audio.object_key,
        mimeType=audio.mime_type,
        bytes=audio.byte_count,
        durationMs=audio.duration_ms,
        startMs=audio.start_ms,
    )


def _contribution_row(
    row: ArtisanConversation, item: ContributionWrite, now: datetime
) -> ArtisanContribution:
    return ArtisanContribution(
        conversationId=row.id,
        userId=row.userId,
        craftId=row.craftId,
        turnId=item.turn_id,
        ordinal=item.ordinal,
        status="PENDING",
        quote=item.quote,
        quoteLanguage=row.language,
        english=item.english,
        englishSource=item.english_source,
        claimText=item.claim_text,
        discipline=item.discipline,
        conceptType=item.concept_type,
        conceptName=item.concept_name,
        startMs=item.start_ms,
        endMs=item.end_ms,
        locatorPrecision=item.precision,
        screens=list(item.screens),
        createdAt=now,
    )


async def _add_seconds(session: AsyncSession, voice: VoiceSession, entry: Any) -> None:
    if await record_units(session, entry):
        voice.reservedSeconds = voice.reservedSeconds + entry.units


def _record(row: ArtisanConversation, craft: CraftRef, district: str | None, role: str) -> ConversationRecord:
    return ConversationRecord(
        id=row.id,
        user_id=row.userId,
        voice_session_id=row.voiceSessionId,
        craft=craft,
        craft_id=row.craftId,
        district=district,
        language=row.language,
        transport=row.transport,
        started_at=row.startedAt,
        ended_at=row.endedAt,
        transcript=row.transcriptEnc,
        topics_asked=tuple(row.topicsAsked or ()),
        extraction=row.extractionStatus,
        attempts=row.extractionAttempts,
        deleted_at=row.deletedAt,
        role=role,
    )
