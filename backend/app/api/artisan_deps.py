from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from app.api.voice_deps import current_voice, voice_runtime, voice_store
from app.core.config import get_settings
from app.core.db import sessionmaker
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.models import User
from app.voice.artisan_availability import HIDDEN_CONVERSATION, conversation_availability
from app.voice.artisan_session import artisan_voice
from app.voice.artisan_store import SqlArtisanStore
from app.voice.runtime import VoiceSettings

__all__ = [
    "artisan_conversation_enabled",
    "artisan_store",
    "artisan_voice_settings",
    "offered_conversation",
    "require_artisan_conversation",
]

logger = logging.getLogger(__name__)


def artisan_conversation_enabled() -> bool:
    return get_settings().artisan_conversation_enabled


def require_artisan_conversation(enabled: bool = Depends(artisan_conversation_enabled)) -> None:
    if not enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")


def artisan_store() -> SqlArtisanStore:
    return SqlArtisanStore(sessionmaker())


async def artisan_voice_settings(voice: VoiceSettings = Depends(current_voice)) -> VoiceSettings:
    return artisan_voice(voice, get_settings().elevenlabs_artisan_agent_id)


async def offered_conversation(
    request: Request,
    user: User = Depends(get_current_user),
    enabled: bool = Depends(artisan_conversation_enabled),
) -> dict[str, Any]:
    if not enabled:
        return dict(HIDDEN_CONVERSATION)
    try:
        voice = await artisan_voice_settings(await current_voice())
        return await conversation_availability(
            user,
            artisans=artisan_store(),
            store=voice_store(),
            runtime=voice_runtime(request),
            voice=voice,
            now=datetime.now(UTC),
        )
    except AppError as error:
        logger.warning("conversation availability could not be read, conversations hidden: %s", error)
        return dict(HIDDEN_CONVERSATION)
