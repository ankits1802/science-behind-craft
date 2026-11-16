from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import TypeAdapter

from app.providers.quota import remaining_today
from app.schemas.voice import VoiceAvailability

from .languages import voice_language_options
from .notice import VOICE_NOTICE_VERSION
from .records import VoiceStore
from .runtime import VoiceRuntime, VoiceSettings
from .seconds import VOICE_SECONDS
from .sessions import VoiceUser, may_use_voice
from .upkeep import settle_own_calls

__all__ = ["HIDDEN_VOICE", "voice_availability"]

AVAILABILITY = TypeAdapter(VoiceAvailability)
HIDDEN_VOICE: dict[str, Any] = {
    "configured": False,
    "transport": None,
    "languages": [],
    "noticeVersion": None,
    "consentRequired": False,
    "remainingSeconds": None,
}


async def voice_availability(
    user: VoiceUser, *, store: VoiceStore, runtime: VoiceRuntime, voice: VoiceSettings, now: datetime
) -> dict[str, Any]:
    if not may_use_voice(user) or voice.missing() or not await runtime.reachable(voice):
        return _checked(HIDDEN_VOICE)
    await settle_own_calls(user.id, store, runtime.elevenlabs(voice))
    remaining = remaining_today(user, VOICE_SECONDS, await store.seconds_used(user.id, now))
    payload = {
        "configured": True,
        "transport": voice.transport,
        "languages": voice_language_options(),
        "noticeVersion": VOICE_NOTICE_VERSION,
        "consentRequired": not await store.consented(user.id, VOICE_NOTICE_VERSION),
        "remainingSeconds": remaining,
    }
    return _checked(payload)


def _checked(payload: dict[str, Any]) -> dict[str, Any]:
    return AVAILABILITY.dump_python(AVAILABILITY.validate_python(payload), mode="json", by_alias=True)
