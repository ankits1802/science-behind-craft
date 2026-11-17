from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings
from app.core.db import sessionmaker
from app.voice.runtime import VoiceRuntime, VoiceSettings, voice_settings
from app.voice.store import SqlVoiceStore

__all__ = ["current_voice", "require_voice_call", "voice_call_enabled", "voice_runtime", "voice_store"]


def voice_runtime(request: Request) -> VoiceRuntime:
    runtime: VoiceRuntime = request.app.state.voice_runtime
    return runtime


def voice_store() -> SqlVoiceStore:
    return SqlVoiceStore(sessionmaker())


async def current_voice() -> VoiceSettings:
    async with sessionmaker()() as session:
        return await voice_settings(session, get_settings())


def voice_call_enabled() -> bool:
    return get_settings().voice_call_enabled


def require_voice_call(enabled: bool = Depends(voice_call_enabled)) -> None:
    if not enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
