from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput, Refused
from app.models import TaskReservation
from app.research.open_work import (
    RESERVATION_TIME,
    RESERVATIONS_HELD_MAX,
    UNRESERVABLE_KINDS,
    OpenTask,
    TaskHold,
    parse_task_key,
)

from .open_work import open_task, proposed_tasks

__all__ = ["TASKS_HELD", "TASK_TAKEN", "claim_task", "complete_task", "release_task"]

TASK_TAKEN = "task_taken"
TASKS_HELD = "tasks_held"
EXPIRED = "EXPIRED"
RELEASED = "RELEASED"
COMPLETED = "COMPLETED"
NOT_OPEN = "No open task has the key {key}; list_open_work gives the open tasks."
QUEUE_NOT_RESERVED = "A review queue is worked item by item in admin settings; it is never reserved."


async def claim_task(
    session: AsyncSession, user_id: uuid.UUID, key: str, *, site: str, now: datetime
) -> TaskHold:
    task = await _open(session, key, site=site)
    await _expire(session, key, now=now)
    current = await _live(session, key)
    if current is not None and current.userId != user_id:
        raise Refused(
            TASK_TAKEN,
            f"{key} is reserved by another account until {current.expiresAt:%Y-%m-%d %H:%M} UTC; "
            "list_open_work gives the tasks still open.",
        )
    if current is not None:
        current.expiresAt = now + RESERVATION_TIME
        await session.flush()
        return _held(key, task, current.expiresAt)
    await _refuse_too_many(session, user_id, now=now)
    reservation = TaskReservation(
        taskKey=key, userId=user_id, reservedAt=now, expiresAt=now + RESERVATION_TIME
    )
    try:
        async with session.begin_nested():
            session.add(reservation)
    except IntegrityError as taken:
        raise Refused(TASK_TAKEN, f"{key} was reserved by another account a moment ago.") from taken
    return _held(key, task, reservation.expiresAt)


async def release_task(session: AsyncSession, user_id: uuid.UUID, key: str, *, now: datetime) -> TaskHold:
    parse_task_key(key)
    current = await _live(session, key)
    if current is None or current.userId != user_id:
        raise InvalidInput(f"You hold no reservation of {key}.")
    _end(current, RELEASED if current.expiresAt > now else EXPIRED, now=now)
    await session.flush()
    return TaskHold(task_key=key, held=False, reserved_until=None)


async def complete_task(session: AsyncSession, user_id: uuid.UUID, key: str, *, now: datetime) -> None:
    current = await _live(session, key)
    if current is not None and current.userId == user_id:
        _end(current, COMPLETED, now=now)
        await session.flush()


async def _open(session: AsyncSession, key: str, *, site: str) -> OpenTask:
    parsed = parse_task_key(key)
    if parsed.kind in UNRESERVABLE_KINDS:
        raise InvalidInput(QUEUE_NOT_RESERVED)
    task = await open_task(session, parsed, site=site)
    if task is None or key in await proposed_tasks(session):
        raise InvalidInput(NOT_OPEN.format(key=key))
    return task


async def _expire(session: AsyncSession, key: str, *, now: datetime) -> None:
    await session.execute(
        update(TaskReservation)
        .where(
            TaskReservation.taskKey == key,
            TaskReservation.endedAt.is_(None),
            TaskReservation.expiresAt <= now,
        )
        .values(endedAt=TaskReservation.expiresAt, ending=EXPIRED)
    )


async def _live(session: AsyncSession, key: str) -> TaskReservation | None:
    return await session.scalar(
        select(TaskReservation).where(TaskReservation.taskKey == key, TaskReservation.endedAt.is_(None))
    )


async def _refuse_too_many(session: AsyncSession, user_id: uuid.UUID, *, now: datetime) -> None:
    held = await session.scalar(
        select(func.count(TaskReservation.id)).where(
            TaskReservation.userId == user_id,
            TaskReservation.endedAt.is_(None),
            TaskReservation.expiresAt > now,
        )
    )
    if (held or 0) >= RESERVATIONS_HELD_MAX:
        raise Refused(
            TASKS_HELD,
            f"This account holds {held} tasks, the most one account may hold at once; release_task one "
            "before claiming another.",
        )


def _end(reservation: TaskReservation, ending: str, *, now: datetime) -> None:
    reservation.endedAt = now if ending != EXPIRED else reservation.expiresAt
    reservation.ending = ending


def _held(key: str, task: OpenTask, until: datetime) -> TaskHold:
    return TaskHold(
        task_key=key, held=True, reserved_until=until, task=task.model_copy(update={"reserved_until": until})
    )
