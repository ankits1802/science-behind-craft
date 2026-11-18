from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.testimony_deps import audio_objects, conversation_turns, refusal, testimony_errors
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.roles import Capability, can
from app.models import ArtisanContribution, ArtisanConversation, User
from app.research.testimony import CONTRIBUTION_STATUSES
from app.services import testimony_store, testimony_writes
from app.services.testimony_views import (
    audio_link,
    contribution_view,
    conversation_detail,
    conversation_summary,
)

router = APIRouter(prefix="/artisan", tags=["artisan"])

Status = Literal[*CONTRIBUTION_STATUSES]
NO_AUDIO = "No recording of this turn is kept."


async def _own_conversation(
    session: AsyncSession, user: User, conversation_id: uuid.UUID
) -> ArtisanConversation:
    conversation = await session.get(ArtisanConversation, conversation_id)
    if conversation is None or conversation.userId != user.id or conversation.deletedAt is not None:
        raise testimony_store.UnknownContribution(f"no conversation {conversation_id} of this account")
    return conversation


@router.get("/conversations")
async def my_conversations(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> Any:
    rows = await session.scalars(
        select(ArtisanConversation)
        .where(ArtisanConversation.userId == user.id, ArtisanConversation.deletedAt.is_(None))
        .order_by(ArtisanConversation.startedAt.desc(), ArtisanConversation.id)
    )
    return {"conversations": [await conversation_summary(session, row) for row in rows]}


@router.get("/conversations/{conversation_id}")
async def my_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    try:
        conversation = await _own_conversation(session, user, conversation_id)
    except testimony_errors as error:
        return refusal(error)
    contributions = await testimony_store.conversation_contributions(session, conversation.id)
    return await conversation_detail(
        session, conversation, contributions, turns=conversation_turns(conversation)
    )


@router.delete("/conversations/{conversation_id}")
async def delete_my_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    try:
        await _own_conversation(session, user, conversation_id)
        withdrawn = await testimony_writes.delete_conversation(
            session, audio_objects(), user, conversation_id, now=datetime.now(UTC)
        )
    except testimony_errors as error:
        await session.rollback()
        return refusal(error)
    await session.commit()
    return {"withdrawn": withdrawn}


@router.get("/contributions")
async def my_contributions(
    status_: Status | None = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    counts, rows = await testimony_store.user_contributions(session, user.id, status=status_)
    return {"counts": counts, "items": [await contribution_view(session, row) for row in rows]}


@router.post("/contributions/{contribution_id}/withdraw")
async def withdraw_my_contribution(
    contribution_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    try:
        withdrawn = await testimony_writes.withdraw(
            session, audio_objects(), user, contribution_id, now=datetime.now(UTC)
        )
    except testimony_errors as error:
        await session.rollback()
        return refusal(error)
    await session.commit()
    return await contribution_view(session, withdrawn)


@router.get("/contributions/{contribution_id}/audio")
async def contribution_audio(
    contribution_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    contribution = await session.get(ArtisanContribution, contribution_id)
    allowed = contribution is not None and (
        contribution.userId == user.id or can(user, Capability.REVIEW_TESTIMONY)
    )
    if contribution is None or not allowed:
        return refusal(testimony_store.UnknownContribution(str(contribution_id)))
    link = await audio_link(session, audio_objects(), contribution, now=datetime.now(UTC))
    if link is None:
        return refusal(testimony_store.UnknownContribution(NO_AUDIO))
    return link
