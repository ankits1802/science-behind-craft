from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArtisanContribution, ArtisanConversation, ArtisanCraft, ArtisanProfile

from . import audit
from .conversation_retention import RETENTION, AudioObjects, purge_conversation, settle_retention
from .testimony_claims import drop_orphans, erase_claim
from .testimony_store import MoveRefused, UnknownContribution, conversation_contributions, owned_contribution

__all__ = [
    "WITHDRAWABLE",
    "NoAudioObjects",
    "UnknownConversation",
    "WithdrawnEverything",
    "clear_expired_rejections",
    "delete_conversation",
    "erase_artisan",
    "withdraw",
    "withdraw_everything",
]

WITHDRAWABLE = ("PENDING", "APPROVED")
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"
CLEAR_BATCH = 500


class UnknownConversation(UnknownContribution):
    pass


class NoAudioObjects:
    async def delete(self, key: str) -> None:
        return None


@dataclass(frozen=True)
class WithdrawnEverything:
    withdrawn_contributions: int
    deleted_conversations: int


def _clear_texts(contribution: ArtisanContribution, now: datetime) -> None:
    contribution.quote = None
    contribution.english = None
    contribution.claimText = None
    contribution.textsClearedAt = now


async def _claim_dropped(session: AsyncSession, contribution: ArtisanContribution, now: datetime) -> None:
    claim_id = contribution.claimId
    contribution.claimId = None
    contribution.version += 1
    _clear_texts(contribution, now)
    await session.flush()
    await erase_claim(session, claim_id)


async def _taken_back(session: AsyncSession, contribution: ArtisanContribution, now: datetime) -> None:
    contribution.status = WITHDRAWN
    contribution.withdrawnAt = now
    contribution.reviewNote = None
    await _claim_dropped(session, contribution, now)


async def _conversation(session: AsyncSession, conversation_id: uuid.UUID) -> ArtisanConversation:
    found = await session.get(ArtisanConversation, conversation_id, with_for_update=True)
    if found is None:
        raise UnknownConversation(f"no conversation {conversation_id}")
    return found


async def _settle(
    session: AsyncSession, objects: AudioObjects | None, conversation: ArtisanConversation, now: datetime
) -> None:
    await drop_orphans(session, conversation)
    until = await settle_retention(session, conversation.id, now=now, at_once=True)
    if until is not None and until <= now:
        await purge_conversation(session, objects or NoAudioObjects(), conversation.id)


async def withdraw(
    session: AsyncSession,
    objects: AudioObjects | None,
    user: Any,
    contribution_id: uuid.UUID,
    *,
    now: datetime,
) -> ArtisanContribution:
    contribution = await owned_contribution(session, user.id, contribution_id, lock=True)
    if contribution.status not in WITHDRAWABLE:
        raise MoveRefused(f"a {contribution.status.lower()} contribution cannot be taken back")
    conversation = await _conversation(session, contribution.conversationId)
    source_status = contribution.status
    await _taken_back(session, contribution, now)
    await session.flush()
    await _settle(session, objects, conversation, now)
    await audit.record(
        session,
        action="testimony.withdrawn",
        actor=user,
        target_type="ArtisanContribution",
        target_id=contribution.id,
        detail={"from": source_status, "to": WITHDRAWN},
    )
    return contribution


async def _empty_conversation(
    session: AsyncSession, objects: AudioObjects | None, conversation: ArtisanConversation, now: datetime
) -> int:
    withdrawn = 0
    for contribution in await conversation_contributions(session, conversation.id):
        if contribution.status in WITHDRAWABLE:
            await _taken_back(session, contribution, now)
            withdrawn += 1
        elif contribution.status == REJECTED and contribution.textsClearedAt is None:
            await _claim_dropped(session, contribution, now)
    await session.flush()
    await drop_orphans(session, conversation)
    conversation.deletedAt = now
    conversation.retentionUntil = now
    await purge_conversation(session, objects or NoAudioObjects(), conversation.id)
    return withdrawn


async def delete_conversation(
    session: AsyncSession,
    objects: AudioObjects | None,
    user: Any,
    conversation_id: uuid.UUID,
    *,
    now: datetime,
) -> int:
    conversation = await _conversation(session, conversation_id)
    if conversation.userId != user.id:
        raise UnknownConversation(f"no conversation {conversation_id} of this account")
    if conversation.deletedAt is not None:
        return 0
    withdrawn = await _empty_conversation(session, objects, conversation, now)
    await audit.record(
        session,
        action="testimony.conversation_deleted",
        actor=user,
        target_type="ArtisanConversation",
        target_id=conversation.id,
        detail={"withdrawn": withdrawn},
    )
    return withdrawn


async def withdraw_everything(
    session: AsyncSession, objects: AudioObjects | None, user: Any, *, now: datetime
) -> WithdrawnEverything:
    conversation_ids = list(
        await session.scalars(
            select(ArtisanConversation.id)
            .where(ArtisanConversation.userId == user.id, ArtisanConversation.deletedAt.is_(None))
            .order_by(ArtisanConversation.startedAt)
        )
    )
    withdrawn = 0
    for conversation_id in conversation_ids:
        conversation = await _conversation(session, conversation_id)
        withdrawn += await _empty_conversation(session, objects, conversation, now)
    if not conversation_ids:
        return WithdrawnEverything(withdrawn_contributions=0, deleted_conversations=0)
    await audit.record(
        session,
        action="testimony.everything_withdrawn",
        actor=user,
        target_type="User",
        target_id=user.id,
        detail={"withdrawn": withdrawn, "conversations": len(conversation_ids)},
    )
    return WithdrawnEverything(withdrawn_contributions=withdrawn, deleted_conversations=len(conversation_ids))


async def erase_artisan(
    session: AsyncSession, objects: AudioObjects | None, user: Any, *, now: datetime
) -> WithdrawnEverything:
    result = await withdraw_everything(session, objects, user, now=now)
    owner = user.id
    await session.execute(delete(ArtisanContribution).where(ArtisanContribution.userId == owner))
    await session.execute(delete(ArtisanConversation).where(ArtisanConversation.userId == owner))
    await session.execute(delete(ArtisanCraft).where(ArtisanCraft.userId == owner))
    await session.execute(delete(ArtisanProfile).where(ArtisanProfile.userId == owner))
    return result


async def clear_expired_rejections(session: AsyncSession, *, now: datetime) -> int:
    expired = list(
        await session.scalars(
            select(ArtisanContribution)
            .where(
                ArtisanContribution.status == REJECTED,
                ArtisanContribution.textsClearedAt.is_(None),
                ArtisanContribution.rejectedAt <= now - RETENTION,
            )
            .order_by(ArtisanContribution.rejectedAt)
            .limit(CLEAR_BATCH)
            .with_for_update(skip_locked=True)
        )
    )
    for contribution in expired:
        await _claim_dropped(session, contribution, now)
    await session.flush()
    for conversation_id in dict.fromkeys(contribution.conversationId for contribution in expired):
        conversation = await session.get(ArtisanConversation, conversation_id)
        if conversation is not None:
            await drop_orphans(session, conversation)
    return len(expired)
