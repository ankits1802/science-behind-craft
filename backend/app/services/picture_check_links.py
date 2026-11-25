from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, String, and_, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Answer, Claim, Concept, Craft, MediaRef as MediaRefRow, MediaRefClaim, PictureCheck
from app.research.crafts import CraftRef
from app.research.picture_checks import (
    DOES_NOT_SHOW,
    PICTURE_CHECK_TASK,
    SHOWS,
    CheckedState,
    StoredVerdict,
    checked_state,
)
from app.research.retrieval import SHOWN_CLAIM_STATUSES
from app.sources.images.picture_files import PICTURE_HOSTS
from app.sources.reference.commons_urls import COMMONS_THUMBS

from . import knowledge_view
from .media_ref_store import TEXT_RELEVANCE, VISION_RELEVANCE, field_media
from .served_pictures import CHOSEN_PICTURE_PROVIDERS

__all__ = [
    "FETCHED_PREFIXES",
    "checked_link",
    "disputed_link",
    "fact_crafts",
    "link_key",
    "searched_link",
    "served_counts",
    "settle_link",
    "unchecked_by",
    "waiting_link",
    "waiting_links",
]

CONCEPT_SUBJECT = "CONCEPT"
FETCHED_PREFIXES = (*(f"https://{host}/" for host in sorted(PICTURE_HOSTS)), COMMONS_THUMBS)


def searched_link() -> ColumnElement[bool]:
    return and_(
        MediaRefRow.id == MediaRefClaim.mediaRefId,
        MediaRefRow.provider.not_in(sorted(CHOSEN_PICTURE_PROVIDERS)),
        MediaRefRow.id.not_in(field_media()),
    )


def waiting_link() -> ColumnElement[bool]:
    fetchable = or_(*(MediaRefRow.imageUrl.startswith(prefix) for prefix in FETCHED_PREFIXES))
    return and_(
        searched_link(),
        fetchable,
        MediaRefClaim.relevance == TEXT_RELEVANCE,
        MediaRefClaim.refusedAt.is_(None),
        Claim.id == MediaRefClaim.claimId,
        Claim.status.in_(SHOWN_CLAIM_STATUSES),
    )


def unchecked_by(user_id: uuid.UUID) -> ColumnElement[bool]:
    return ~exists().where(PictureCheck.linkId == MediaRefClaim.id, PictureCheck.userId == user_id)


def disputed_link() -> ColumnElement[bool]:
    ruled = exists().where(PictureCheck.linkId == MediaRefClaim.id, PictureCheck.ruling.is_(True))
    return and_(_given(SHOWS), _given(DOES_NOT_SHOW), ~ruled)


def link_key() -> ColumnElement[str]:
    return func.concat(f"{PICTURE_CHECK_TASK}:", cast(MediaRefClaim.id, String))


def served_counts() -> Any:
    cited = select(func.unnest(Answer.claimIds).label("claimId")).subquery()
    return select(cited.c.claimId, func.count().label("served")).group_by(cited.c.claimId).subquery()


async def waiting_links(session: AsyncSession) -> int:
    counted = await session.scalar(
        select(func.count(MediaRefClaim.id))
        .select_from(MediaRefClaim, MediaRefRow, Claim)
        .where(waiting_link())
    )
    return int(counted or 0)


async def checked_link(session: AsyncSession, link_id: uuid.UUID) -> MediaRefClaim | None:
    return await session.scalar(
        select(MediaRefClaim)
        .select_from(MediaRefClaim, MediaRefRow)
        .where(MediaRefClaim.id == link_id, searched_link())
    )


async def settle_link(session: AsyncSession, link: MediaRefClaim, *, now: datetime) -> CheckedState:
    rows = await session.execute(
        select(PictureCheck.userId, PictureCheck.verdict, PictureCheck.trusted, PictureCheck.ruling)
        .where(PictureCheck.linkId == link.id)
        .order_by(PictureCheck.createdAt, PictureCheck.id)
    )
    verdicts = [
        StoredVerdict(user_id=user_id, shows=verdict == SHOWS, trusted=trusted, ruling=ruling)
        for user_id, verdict, trusted, ruling in rows.all()
    ]
    state = checked_state(verdicts)
    link.relevance = VISION_RELEVANCE if state.vision else TEXT_RELEVANCE
    if not state.refused:
        link.refusedAt = None
    elif link.refusedAt is None:
        link.refusedAt = now
    await session.flush()
    return state


async def fact_crafts(session: AsyncSession, claim_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, CraftRef]:
    if not claim_ids:
        return {}
    rows = await session.execute(
        select(Claim.id, Craft)
        .join(Concept, and_(Claim.subjectType == CONCEPT_SUBJECT, Concept.id == Claim.subjectId))
        .join(Craft, Craft.id == Concept.craftId)
        .where(Claim.id.in_(list(dict.fromkeys(claim_ids))))
    )
    return {
        claim_id: CraftRef.model_validate(knowledge_view.craft_ref(craft))
        for claim_id, craft in rows.tuples()
    }


def _given(verdict: str) -> ColumnElement[bool]:
    return exists().where(
        PictureCheck.linkId == MediaRefClaim.id,
        PictureCheck.verdict == verdict,
        PictureCheck.ruling.is_(False),
    )
