from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import TypeAdapter

from app.core.roles import ARTISAN, Capability, can, role_value
from app.providers.quota import remaining_today
from app.research.testimony import RECORDING_NOTICE_VERSION
from app.schemas.artisan import ConversationAvailability

from .artisan_records import ArtisanStore
from .languages import voice_language_options
from .records import VoiceStore
from .runtime import VoiceRuntime, VoiceSettings
from .seconds import VOICE_SECONDS
from .sessions import VoiceUser

__all__ = ["HIDDEN_CONVERSATION", "conversation_availability", "may_converse"]

AVAILABILITY = TypeAdapter(ConversationAvailability)
HIDDEN_CONVERSATION: dict[str, Any] = {
    "configured": False,
    "transport": None,
    "languages": [],
    "noticeVersion": None,
    "consentRequired": False,
    "remainingSeconds": None,
    "crafts": [],
}


def may_converse(user: VoiceUser) -> bool:
    return (
        role_value(user) == ARTISAN
        and can(user, Capability.CONTRIBUTE_TESTIMONY)
        and user.emailVerifiedAt is not None
    )


async def conversation_availability(
    user: VoiceUser,
    *,
    artisans: ArtisanStore,
    store: VoiceStore,
    runtime: VoiceRuntime,
    voice: VoiceSettings,
    now: datetime,
) -> dict[str, Any]:
    if not may_converse(user) or voice.missing() or not await runtime.reachable(voice):
        return dict(HIDDEN_CONVERSATION)
    facts = await artisans.facts(user.id)
    if not facts.crafts:
        return dict(HIDDEN_CONVERSATION)
    remaining = remaining_today(user, VOICE_SECONDS, await store.seconds_used(user.id, now))
    consented = facts.consent is not None and facts.consent[1] == RECORDING_NOTICE_VERSION
    payload = {
        "configured": True,
        "transport": voice.transport,
        "languages": voice_language_options(),
        "noticeVersion": RECORDING_NOTICE_VERSION,
        "consentRequired": not consented,
        "remainingSeconds": remaining,
        "crafts": [craft.model_dump(mode="json", by_alias=True) for _, craft in facts.crafts],
    }
    return AVAILABILITY.dump_python(AVAILABILITY.validate_python(payload), mode="json", by_alias=True)
