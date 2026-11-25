from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, case, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Claim, MediaRef as MediaRefRow, MediaRefClaim, TaskReservation, User
from app.research.crafts import CraftRef
from app.research.media_refs import MediaRef
from app.research.open_work import RESERVATION_TIME
from app.research.picture_checks import PictureToCheck, check_key
from app.sources.http import source_client
from app.sources.images.picture_files import picture_files
from app.sources.reference.commons_urls import commons_thumbnail_url, commons_upload_url

from . import trust_tiers
from .export_pictures import Picture, PictureSource, export_pictures
from .media_ref_store import stored_media_ref
from .picture_check_links import fact_crafts, link_key, served_counts, unchecked_by, waiting_link
from .task_reservations import end_expired, holding

__all__ = [
    "CHECK_FETCH_SECONDS",
    "CHECK_WIDTH",
    "CheckBatch",
    "ShownCheck",
    "check_picture_url",
    "check_source",
    "take_batch",
]

CHECK_WIDTH = 330
CHECK_FETCH_SECONDS = 8.0
CANDIDATES_PER_PLACE = 2


@dataclass(frozen=True)
class ShownCheck:
    item: PictureToCheck
    picture: Picture


@dataclass(frozen=True)
class CheckBatch:
    shown: list[ShownCheck]
    skipped: int
    full: bool


@dataclass(frozen=True)
class _Candidate:
    link_id: uuid.UUID
    claim_id: uuid.UUID
    media: MediaRef
    fact: str
    served: int
    held: bool


@dataclass(frozen=True)
class _Ask:
    id: uuid.UUID
    image_url: str


def check_picture_url(media: MediaRef) -> str:
    upload = commons_upload_url(media.image_url)
    return commons_thumbnail_url(upload, CHECK_WIDTH) or upload


@asynccontextmanager
async def check_source() -> AsyncIterator[PictureSource]:
    async with source_client(get_settings().research_contact_email) as client:
        yield picture_files(client)


async def take_batch(
    session: AsyncSession, user: User, *, take: int, source: PictureSource, now: datetime
) -> CheckBatch:
    found = await _candidates(session, user.id, now=now, limit=take * CANDIDATES_PER_PLACE)
    asks = [_Ask(each.media.id, check_picture_url(each.media)) for each in found]
    read = await export_pictures(asks, source, within=CHECK_FETCH_SECONDS)
    crafts = await fact_crafts(session, [each.claim_id for each in found])
    room = await _room(session, user.id, now=now)
    shown: list[ShownCheck] = []
    for each in found:
        picture = read.found.get(each.media.id)
        if picture is None or len(shown) == take or (room <= 0 and not each.held):
            continue
        until = await _reserved(session, user.id, each, now=now)
        if until is None:
            continue
        room -= 0 if each.held else 1
        shown.append(ShownCheck(_item(len(shown) + 1, each, crafts, until), picture))
    skipped = sum(each.media.id not in read.found for each in found)
    return CheckBatch(shown=shown, skipped=skipped, full=room <= 0 and len(shown) < take)


async def _room(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> int:
    standing = await trust_tiers.account_standing(session, user_id)
    return standing.tasks_held_max - await holding(session, user_id, now=now)


async def _candidates(
    session: AsyncSession, user_id: uuid.UUID, *, now: datetime, limit: int
) -> list[_Candidate]:
    served = served_counts()
    live = and_(
        TaskReservation.taskKey == link_key(),
        TaskReservation.endedAt.is_(None),
        TaskReservation.expiresAt > now,
    )
    mine = exists().where(live, TaskReservation.userId == user_id)
    theirs = exists().where(live, TaskReservation.userId != user_id)
    rows = await session.execute(
        select(MediaRefClaim.id, MediaRefClaim.claimId, MediaRefRow, Claim.text, served.c.served, mine)
        .select_from(MediaRefClaim)
        .join(MediaRefRow, MediaRefRow.id == MediaRefClaim.mediaRefId)
        .join(Claim, Claim.id == MediaRefClaim.claimId)
        .outerjoin(served, served.c.claimId == MediaRefClaim.claimId)
        .where(waiting_link(), unchecked_by(user_id), ~theirs)
        .order_by(
            case((mine, 0), else_=1),
            func.coalesce(served.c.served, 0).desc(),
            MediaRefClaim.createdAt,
            MediaRefClaim.id,
        )
        .limit(limit)
    )
    return [
        _Candidate(link_id, claim_id, stored_media_ref(row), text, int(count or 0), bool(held))
        for link_id, claim_id, row, text, count, held in rows.tuples()
    ]


async def _reserved(
    session: AsyncSession, user_id: uuid.UUID, candidate: _Candidate, *, now: datetime
) -> datetime | None:
    key = check_key(candidate.link_id)
    if candidate.held:
        held = await session.scalar(
            select(TaskReservation).where(TaskReservation.taskKey == key, TaskReservation.endedAt.is_(None))
        )
        if held is None or held.userId != user_id:
            return None
        held.expiresAt = now + RESERVATION_TIME
        await session.flush()
        return held.expiresAt
    await end_expired(session, key, now=now)
    reservation = TaskReservation(
        taskKey=key, userId=user_id, reservedAt=now, expiresAt=now + RESERVATION_TIME
    )
    try:
        async with session.begin_nested():
            session.add(reservation)
    except IntegrityError:
        return None
    return reservation.expiresAt


def _item(
    position: int, candidate: _Candidate, crafts: Mapping[uuid.UUID, CraftRef], until: datetime
) -> PictureToCheck:
    media = candidate.media
    return PictureToCheck(
        position=position,
        link_id=candidate.link_id,
        fact_id=candidate.claim_id,
        fact=candidate.fact,
        craft=crafts.get(candidate.claim_id),
        title=media.title,
        caption=media.alt,
        credit=media.credit,
        page_url=media.page_url,
        served=candidate.served,
        reserved_until=until,
    )
