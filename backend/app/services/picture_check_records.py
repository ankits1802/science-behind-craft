from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import MediaRefClaim, PictureCheck, TaskReservation, User
from app.research.picture_checks import (
    DOES_NOT_SHOW,
    SHOWS,
    CheckedState,
    RecordedCheck,
    check_key,
    state_word,
)

from .picture_check_links import checked_link, settle_link
from .task_reservations import complete_task

__all__ = [
    "CHECKED_ONCE",
    "NOT_SEARCHED",
    "RESERVED_ELSEWHERE",
    "RULED",
    "GivenVerdict",
    "Recorded",
    "record_verdict",
]

NOT_SEARCHED = "No searched picture's link has the id {link_id}; check_pictures gives the links to check."
RULED = "An Admin decided this picture beside this fact; it is checked no more."
CHECKED_ONCE = "This account already checked this picture beside this fact; one account checks a link once."
RESERVED_ELSEWHERE = "Another account holds this link in its batch until {until:%Y-%m-%d %H:%M} UTC."


@dataclass(frozen=True)
class GivenVerdict:
    link_id: uuid.UUID
    shows: bool
    reason: str


@dataclass(frozen=True)
class Recorded:
    check: RecordedCheck
    claim_id: uuid.UUID
    state: CheckedState


async def record_verdict(
    session: AsyncSession, user: User, given: GivenVerdict, *, trusted: bool, now: datetime
) -> Recorded:
    link = await checked_link(session, given.link_id)
    if link is None:
        raise InvalidInput(NOT_SEARCHED.format(link_id=given.link_id))
    await _refuse_closed(session, link, user.id, now=now)
    verdict = PictureCheck(
        linkId=link.id,
        userId=user.id,
        verdict=SHOWS if given.shows else DOES_NOT_SHOW,
        reason=given.reason,
        trusted=trusted,
        createdAt=now,
    )
    try:
        async with session.begin_nested():
            session.add(verdict)
    except IntegrityError as twice:
        raise InvalidInput(CHECKED_ONCE) from twice
    state = await settle_link(session, link, now=now)
    await complete_task(session, user.id, check_key(link.id), now=now)
    return Recorded(RecordedCheck(link_id=link.id, state=state_word(state)), link.claimId, state)


async def _refuse_closed(
    session: AsyncSession, link: MediaRefClaim, user_id: uuid.UUID, *, now: datetime
) -> None:
    ruled = exists().where(PictureCheck.linkId == link.id, PictureCheck.ruling.is_(True))
    if await session.scalar(select(ruled)):
        raise InvalidInput(RULED)
    mine = exists().where(PictureCheck.linkId == link.id, PictureCheck.userId == user_id)
    if await session.scalar(select(mine)):
        raise InvalidInput(CHECKED_ONCE)
    held = await session.scalar(
        select(TaskReservation).where(
            TaskReservation.taskKey == check_key(link.id),
            TaskReservation.endedAt.is_(None),
            TaskReservation.expiresAt > now,
        )
    )
    if held is not None and held.userId != user_id:
        raise InvalidInput(RESERVED_ELSEWHERE.format(until=held.expiresAt))
