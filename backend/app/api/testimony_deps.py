from __future__ import annotations

from fastapi import status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import InvalidInput
from app.models import ArtisanConversation
from app.services.object_store import ObjectStore, media_bucket
from app.services.testimony_store import (
    STALE_DETAIL,
    ContributionProblems,
    MoveRefused,
    OwnContribution,
    StaleContribution,
    UnknownContribution,
)
from app.services.testimony_views import Turns, turns_by_id
from app.voice.privacy import transcript_cipher

__all__ = ["NOT_FOUND_DETAIL", "audio_objects", "conversation_turns", "refusal", "testimony_errors"]

NOT_FOUND_DETAIL = "No contribution or conversation has that address."
MOVE_DETAIL = "This contribution cannot be changed that way now."
OWN_DETAIL = "Someone else reviews your own words."
testimony_errors = (
    UnknownContribution,
    StaleContribution,
    MoveRefused,
    OwnContribution,
    ContributionProblems,
    InvalidInput,
)


def conversation_turns(conversation: ArtisanConversation | None) -> Turns:
    if conversation is None or not conversation.transcriptEnc:
        return {}
    cipher = transcript_cipher(get_settings().transcript_encryption_key)
    return turns_by_id(cipher.open(conversation.transcriptEnc))


def audio_objects() -> ObjectStore | None:
    return media_bucket()


def refusal(error: Exception) -> JSONResponse:
    if isinstance(error, UnknownContribution):
        return JSONResponse({"detail": NOT_FOUND_DETAIL}, status.HTTP_404_NOT_FOUND)
    if isinstance(error, StaleContribution):
        return JSONResponse({"detail": STALE_DETAIL}, status.HTTP_409_CONFLICT)
    if isinstance(error, MoveRefused):
        return JSONResponse({"detail": MOVE_DETAIL}, status.HTTP_409_CONFLICT)
    if isinstance(error, OwnContribution):
        return JSONResponse({"detail": OWN_DETAIL}, status.HTTP_403_FORBIDDEN)
    problems = error.problems if isinstance(error, ContributionProblems) else [str(error)]
    return JSONResponse(
        {"detail": "; ".join(problems), "problems": problems}, status.HTTP_422_UNPROCESSABLE_CONTENT
    )
