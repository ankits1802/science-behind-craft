from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArtisanContribution, ArtisanConversation, ArtisanConversationAudio, Craft, User
from app.research.testimony import AUDIO_LINK_SECONDS, Speaker
from app.research.vocabulary import language_option

from .knowledge_view import claims_by_id, craft_ref
from .naming import content_disposition
from .testimony_claims import contribution_locator, conversation_speaker
from .testimony_store import UnknownContribution, status_counts

__all__ = [
    "AudioLinks",
    "Turns",
    "audio_link",
    "contribution_view",
    "conversation_detail",
    "conversation_summary",
    "review_item",
    "turns_by_id",
]

Turns = Mapping[str, Mapping[str, Any]]
KALAVIGYAN = "KALAVIGYAN"


class AudioLinks(Protocol):
    def presigned_get(self, key: str, *, disposition: str, seconds: int, now: datetime) -> Any: ...


def turns_by_id(opened: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    turns = (opened or {}).get("turns") or []
    return {str(turn.get("id")): turn for turn in turns if isinstance(turn, Mapping) and turn.get("id")}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _speaker_payload(credit: Speaker) -> dict[str, Any]:
    return {
        "name": credit.name,
        "role": credit.role,
        "district": credit.district or None,
        "state": credit.state or None,
    }


async def _reviewer_role(session: AsyncSession, reviewer_id: uuid.UUID | None) -> str | None:
    if reviewer_id is None:
        return None
    role = await session.scalar(select(User.role).where(User.id == reviewer_id))
    return str(getattr(role, "value", role)) if role is not None else None


async def _context(
    session: AsyncSession, contribution: ArtisanContribution
) -> tuple[Craft, ArtisanConversation]:
    craft = await session.get(Craft, contribution.craftId)
    conversation = await session.get(ArtisanConversation, contribution.conversationId)
    if craft is None or conversation is None:
        raise UnknownContribution(f"contribution {contribution.id} has lost its craft or conversation")
    return craft, conversation


async def contribution_view(session: AsyncSession, contribution: ArtisanContribution) -> dict[str, Any]:
    if contribution.status == "WITHDRAWN":
        return {
            "id": str(contribution.id),
            "status": contribution.status,
            "conversationId": str(contribution.conversationId),
            "withdrawnAt": _iso(contribution.withdrawnAt),
        }
    craft, conversation = await _context(session, contribution)
    credit = await conversation_speaker(session, contribution.userId, craft)
    return {
        "id": str(contribution.id),
        "status": contribution.status,
        "conversationId": str(contribution.conversationId),
        "craft": craft_ref(craft),
        "discipline": contribution.discipline,
        "claimText": contribution.claimText,
        "quote": contribution.quote,
        "language": contribution.quoteLanguage,
        "english": contribution.english,
        "englishSource": contribution.englishSource,
        "locator": contribution_locator(contribution),
        "recordedAt": _iso(conversation.startedAt),
        "line": credit.line,
        "submittedAt": _iso(contribution.createdAt),
        "reviewedAt": _iso(contribution.reviewedAt),
        "reviewerRole": await _reviewer_role(session, contribution.reviewedById),
        "rejectReason": contribution.rejectReason,
        "reviewNote": contribution.reviewNote,
        "approvedAt": _iso(contribution.approvedAt),
        "withdrawnAt": _iso(contribution.withdrawnAt),
    }


async def audio_link(
    session: AsyncSession, links: AudioLinks | None, contribution: ArtisanContribution, *, now: datetime
) -> dict[str, Any] | None:
    if links is None or contribution.status not in ("PENDING", "APPROVED"):
        return None
    audio = await session.scalar(
        select(ArtisanConversationAudio).where(
            ArtisanConversationAudio.conversationId == contribution.conversationId,
            ArtisanConversationAudio.turnId == contribution.turnId,
        )
    )
    if audio is None:
        return None
    leaf = audio.objectKey.rsplit("/", 1)[-1]
    link = links.presigned_get(
        audio.objectKey,
        disposition=content_disposition(leaf, inline=True),
        seconds=AUDIO_LINK_SECONDS,
        now=now,
    )
    return {
        "url": link.url,
        "expiresAt": link.expires_at.isoformat(),
        "mimeType": audio.mimeType,
        "startMs": max(contribution.startMs - audio.startMs, 0),
        "endMs": max(contribution.endMs - audio.startMs, 0),
    }


def _turn_before(turns: Turns, turn: Mapping[str, Any] | None) -> dict[str, Any]:
    ordinal = int((turn or {}).get("ordinal") or 0)
    earlier = [
        t for t in turns.values() if t.get("speaker") == KALAVIGYAN and int(t.get("ordinal") or 0) < ordinal
    ]
    before = max(earlier, key=lambda t: int(t.get("ordinal") or 0), default={})
    return {"text": before.get("text"), "english": before.get("english"), "answerId": before.get("answerId")}


async def _corroborations(session: AsyncSession, claim_ids: Sequence[uuid.UUID]) -> list[dict[str, Any]]:
    views, _sources = await claims_by_id(session, claim_ids)
    return [
        views[claim_id].citations[0]
        for claim_id in claim_ids
        if claim_id in views and views[claim_id].citations
    ]


def _closed_item(contribution: ArtisanContribution, craft: Craft) -> dict[str, Any]:
    return {
        "id": str(contribution.id),
        "status": contribution.status,
        "craft": craft_ref(craft),
        "withdrawnAt": _iso(contribution.withdrawnAt),
    }


async def _review_context(
    session: AsyncSession,
    contribution: ArtisanContribution,
    *,
    turns: Turns,
    links: AudioLinks | None,
    now: datetime,
) -> dict[str, Any]:
    turn = turns.get(str(contribution.turnId))
    return {
        "before": _turn_before(turns, turn),
        "turnText": (turn or {}).get("text"),
        "audio": await audio_link(session, links, contribution, now=now),
    }


async def review_item(
    session: AsyncSession,
    contribution: ArtisanContribution,
    *,
    turns: Turns,
    links: AudioLinks | None,
    now: datetime,
) -> dict[str, Any]:
    craft, conversation = await _context(session, contribution)
    if contribution.status == "WITHDRAWN" or contribution.textsClearedAt is not None:
        return _closed_item(contribution, craft)
    credit = await conversation_speaker(session, contribution.userId, craft)
    option = language_option(contribution.quoteLanguage)
    corroborated = await _corroborations(session, list(contribution.corroboratingClaimIds or []))
    return {
        "id": str(contribution.id),
        "version": contribution.version,
        "status": contribution.status,
        "craft": craft_ref(craft),
        "discipline": contribution.discipline,
        "conceptType": contribution.conceptType,
        "conceptName": contribution.conceptName,
        "claimText": contribution.claimText,
        "quote": contribution.quote,
        "language": contribution.quoteLanguage,
        "script": option["script"],
        "direction": option["direction"],
        "english": contribution.english,
        "englishSource": contribution.englishSource,
        "locator": contribution_locator(contribution),
        "locatorPrecision": contribution.locatorPrecision,
        "recordedAt": _iso(conversation.startedAt),
        "speaker": _speaker_payload(credit),
        "line": credit.line,
        "screens": list(contribution.screens or []),
        "corroboratedBy": corroborated,
        "context": await _review_context(session, contribution, turns=turns, links=links, now=now),
        **(await _review_marks(session, contribution)),
    }


async def _review_marks(session: AsyncSession, contribution: ArtisanContribution) -> dict[str, Any]:
    return {
        "submittedAt": _iso(contribution.createdAt),
        "reviewedAt": _iso(contribution.reviewedAt),
        "reviewerRole": await _reviewer_role(session, contribution.reviewedById),
        "rejectReason": contribution.rejectReason,
        "reviewNote": contribution.reviewNote,
    }


def _duration(conversation: ArtisanConversation) -> int | None:
    if conversation.endedAt is None:
        return None
    return max(int((conversation.endedAt - conversation.startedAt).total_seconds()), 0)


async def conversation_summary(session: AsyncSession, conversation: ArtisanConversation) -> dict[str, Any]:
    craft = await session.get(Craft, conversation.craftId)
    counts = await status_counts(session, ArtisanContribution.conversationId == conversation.id)
    return {
        "id": str(conversation.id),
        "craft": craft_ref(craft) if craft is not None else None,
        "language": conversation.language,
        "startedAt": _iso(conversation.startedAt),
        "endedAt": _iso(conversation.endedAt),
        "durationSeconds": _duration(conversation),
        "extraction": conversation.extractionStatus,
        "contributions": counts,
        "retentionUntil": _iso(conversation.retentionUntil),
    }


def _shown_turn(turn: Mapping[str, Any], kept: set[str]) -> dict[str, Any]:
    return {
        "ordinal": turn.get("ordinal"),
        "speaker": turn.get("speaker"),
        "text": turn.get("text"),
        "english": turn.get("english"),
        "answerId": turn.get("answerId"),
        "startMs": turn.get("startMs"),
        "endMs": turn.get("endMs"),
        "hasAudio": str(turn.get("id")) in kept,
    }


async def conversation_detail(
    session: AsyncSession,
    conversation: ArtisanConversation,
    contributions: Sequence[ArtisanContribution],
    *,
    turns: Turns,
) -> dict[str, Any]:
    craft = await session.get(Craft, conversation.craftId)
    kept = {
        str(turn_id)
        for turn_id in await session.scalars(
            select(ArtisanConversationAudio.turnId).where(
                ArtisanConversationAudio.conversationId == conversation.id
            )
        )
    }
    ordered = sorted(turns.values(), key=lambda turn: int(turn.get("ordinal") or 0))
    return {
        "conversationId": str(conversation.id),
        "craft": craft_ref(craft) if craft is not None else None,
        "language": conversation.language,
        "startedAt": _iso(conversation.startedAt),
        "endedAt": _iso(conversation.endedAt),
        "retentionUntil": _iso(conversation.retentionUntil),
        "turns": [_shown_turn(turn, kept) for turn in ordered],
        "contributions": [await contribution_view(session, item) for item in contributions],
    }
