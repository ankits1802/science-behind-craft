from __future__ import annotations

import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import INDIA_TZ
from app.data.craft_names import load_craft_names
from app.models import (
    ArtisanContribution,
    ArtisanConversation,
    ArtisanProfile,
    Claim,
    ClaimSource,
    Concept,
    Craft,
    ReviewEvent,
    Source,
)
from app.research.testimony import SPEAKER_ROLE, Speaker, speaker, time_locator

from .field_voices_credit import long_date
from .orphan_concepts import concept_unlinked
from .reader_profiles import district_names

__all__ = [
    "ARTISAN_ORIGIN",
    "CONTRIBUTION_ORIGIN",
    "ERASED_STATUS",
    "ERASED_TEXT",
    "ERASURE_ACTOR",
    "FOUND_BY",
    "PREDICATE",
    "TESTIMONY_CONCEPT_REF",
    "TESTIMONY_SENSITIVITY",
    "ClaimWrite",
    "claim_versions",
    "contribution_locator",
    "conversation_speaker",
    "craft_display_name",
    "drop_orphans",
    "ensure_source",
    "erase_claim",
    "fold_name",
    "rewrite_credit",
    "testimony_concept",
    "write_claim",
]

ARTISAN_ORIGIN = "ARTISAN"
CONTRIBUTION_ORIGIN = "CONTRIBUTION"
TESTIMONY_SENSITIVITY = "ATTRIBUTE_REQUIRED"
TESTIMONY_CONCEPT_REF = "artisan-testimony"
PREDICATE = "artisan_testimony"
FOUND_BY = "artisan_conversation"
PUBLISHER = "KalaVigyan"
EVIDENCE_KIND = "artisan testimony"
ERASED_TEXT = "Withdrawn by its speaker."
ERASED_STATUS = "WITHDRAWN"
ERASURE_ACTOR = "testimony_erasure"
ERASED_VALUES: dict[str, Any] = {
    "text": ERASED_TEXT,
    "status": ERASED_STATUS,
    "valueNum": None,
    "valueUnit": None,
    "levelReason": None,
    "embedding": None,
    "createdById": None,
}


@dataclass(frozen=True, kw_only=True)
class ClaimWrite:
    contribution: ArtisanContribution
    concept_id: uuid.UUID
    source_id: uuid.UUID
    reviewer_id: uuid.UUID
    now: datetime
    supersedes: uuid.UUID | None = None


def craft_display_name(craft: Craft) -> str:
    return load_craft_names().display_name(craft.slug, craft.name)


def fold_name(name: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


def contribution_locator(contribution: ArtisanContribution) -> str:
    return time_locator(contribution.startMs, contribution.endMs, contribution.locatorPrecision)


async def conversation_speaker(session: AsyncSession, user_id: uuid.UUID, craft: Craft) -> Speaker:
    shown = craft_display_name(craft)
    profile = await session.get(ArtisanProfile, user_id)
    place = await district_names(session, profile.districtLgd) if profile is not None else None
    if profile is None or place is None:
        return Speaker(name=None, role=SPEAKER_ROLE, district="", state="", line=f"An artisan of {shown}")
    return speaker(
        mode=profile.creditMode,
        name=profile.creditName,
        short_name=profile.creditShortName,
        craft=shown,
        district=place.name,
        state=place.state_name,
    )


def _source_credit(source: Source, credit: Speaker) -> None:
    source.authors = [{"name": credit.name}] if credit.name else []
    source.attribution = credit.line


async def ensure_source(session: AsyncSession, conversation: ArtisanConversation, craft: Craft) -> Source:
    if conversation.sourceId is not None:
        found = await session.get(Source, conversation.sourceId)
        if found is not None:
            return found
    recorded = (conversation.endedAt or conversation.startedAt).astimezone(INDIA_TZ)
    source = Source(
        kind="FIELD_TESTIMONY",
        title=f"Artisan conversation, {craft_display_name(craft)}, {long_date(recorded.date())}",
        year=recorded.year,
        publisher=PUBLISHER,
        url=None,
        storage="EXCERPT",
        sensitivity=TESTIMONY_SENSITIVITY,
        origin=CONTRIBUTION_ORIGIN,
        reliability="C",
        evidenceKind=EVIDENCE_KIND,
        externalIds={"kalavigyan": {"conversationId": str(conversation.id)}},
        retrievedAt=conversation.endedAt or conversation.startedAt,
    )
    _source_credit(source, await conversation_speaker(session, conversation.userId, craft))
    session.add(source)
    await session.flush()
    conversation.sourceId = source.id
    return source


async def testimony_concept(session: AsyncSession, craft_id: uuid.UUID, kind: str, name: str) -> Concept:
    wanted = fold_name(name)
    candidates = await session.scalars(
        select(Concept).where(
            Concept.craftId == craft_id,
            Concept.type == kind,
            Concept.sensitivity == TESTIMONY_SENSITIVITY,
            Concept.originRef == TESTIMONY_CONCEPT_REF,
        )
    )
    for concept in candidates:
        if fold_name(concept.name) == wanted:
            return concept
    concept = Concept(
        craftId=craft_id,
        type=kind,
        name=" ".join(name.split()),
        sensitivity=TESTIMONY_SENSITIVITY,
        originRef=TESTIMONY_CONCEPT_REF,
    )
    session.add(concept)
    await session.flush()
    return concept


async def write_claim(session: AsyncSession, write: ClaimWrite) -> Claim:
    contribution = write.contribution
    shown_on = long_date(write.now.astimezone(INDIA_TZ).date())
    claim = Claim(
        subjectType="CONCEPT",
        subjectId=write.concept_id,
        predicate=PREDICATE,
        text=contribution.claimText,
        textLang="en",
        evidenceLevel="PROVISIONAL",
        levelReason=f"Artisan testimony, approved for showing {shown_on}; not independently confirmed",
        origin=ARTISAN_ORIGIN,
        status="APPROVED",
        supersedesId=write.supersedes,
        createdById=contribution.userId,
        createdByKind="USER",
        sensitivity=TESTIMONY_SENSITIVITY,
        field=contribution.discipline,
    )
    session.add(claim)
    await session.flush()
    session.add(
        ClaimSource(
            claimId=claim.id,
            sourceId=write.source_id,
            quote=contribution.quote,
            locator=contribution_locator(contribution),
            quoteCheck="PASS",
            checkedAt=write.now,
            relation="DIRECT",
            foundBy=FOUND_BY,
            retrievedAt=write.now,
        )
    )
    session.add(
        ReviewEvent(claimId=claim.id, actorId=write.reviewer_id, actorKind="USER", toStatus="APPROVED")
    )
    return claim


async def claim_versions(session: AsyncSession, claim_id: uuid.UUID | None) -> list[uuid.UUID]:
    versions: list[uuid.UUID] = []
    current = claim_id
    while current is not None and current not in versions:
        versions.append(current)
        current = await session.scalar(select(Claim.supersedesId).where(Claim.id == current))
    return versions


async def erase_claim(session: AsyncSession, claim_id: uuid.UUID | None) -> int:
    versions = await claim_versions(session, claim_id)
    if not versions:
        return 0
    claims = list(await session.scalars(select(Claim).where(Claim.id.in_(versions))))
    events = [
        ReviewEvent(
            claimId=claim.id,
            actorKind="SYSTEM",
            systemActor=ERASURE_ACTOR,
            fromStatus=claim.status,
            toStatus=ERASED_STATUS,
        )
        for claim in claims
        if claim.status != ERASED_STATUS
    ]
    await session.execute(delete(ClaimSource).where(ClaimSource.claimId.in_(versions)))
    await session.execute(update(Claim).where(Claim.id.in_(versions)).values(ERASED_VALUES))
    for event in events:
        session.add(event)
    return len(versions)


async def drop_orphans(session: AsyncSession, conversation: ArtisanConversation) -> None:
    source_id = conversation.sourceId
    if source_id is not None:
        cited = await session.scalar(select(func.count()).where(ClaimSource.sourceId == source_id))
        if not cited:
            conversation.sourceId = None
            await session.execute(delete(Source).where(Source.id == source_id))
    resting = exists().where(
        Claim.subjectType == "CONCEPT", Claim.subjectId == Concept.id, Claim.status != ERASED_STATUS
    )
    await session.execute(
        delete(Concept).where(
            Concept.craftId == conversation.craftId,
            Concept.originRef == TESTIMONY_CONCEPT_REF,
            Concept.sensitivity == TESTIMONY_SENSITIVITY,
            ~resting,
            concept_unlinked(),
        )
    )


async def rewrite_credit(session: AsyncSession, user: Any) -> int:
    user_id = user.id
    rows = await session.execute(
        select(Source, Craft)
        .join(ArtisanConversation, ArtisanConversation.sourceId == Source.id)
        .join(Craft, Craft.id == ArtisanConversation.craftId)
        .where(ArtisanConversation.userId == user_id)
    )
    changed = 0
    for source, craft in rows:
        _source_credit(source, await conversation_speaker(session, user_id, craft))
        changed += 1
    return changed
