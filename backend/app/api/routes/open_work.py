from __future__ import annotations

from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import public_reader
from app.core.config import get_settings
from app.core.db import get_session
from app.core.deps import require
from app.core.errors import InvalidInput, Refused
from app.core.roles import Capability, role_value
from app.models import User
from app.research.base import ContractModel
from app.research.open_work import TASK_KEY_MAX_CHARS, OpenWork, TaskHold, Viewer, WorkFilters
from app.services import open_work, task_reservations

router = APIRouter(prefix="/knowledge/open-work", tags=["knowledge"])
contributor = require(Capability.PROPOSE_KNOWLEDGE)


class TaskKeyBody(ContractModel):
    task_key: str = Field(min_length=1, max_length=TASK_KEY_MAX_CHARS)


@router.get("")
async def list_open_work(
    filters: Annotated[WorkFilters, Query()],
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
) -> OpenWork:
    try:
        return await open_work.list_open_work(session, filters, _viewer(reader), site=_site(), now=_now())
    except InvalidInput as invalid:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(invalid)) from invalid


@router.post("/claim")
async def claim_task(
    body: TaskKeyBody, user: User = Depends(contributor), session: AsyncSession = Depends(get_session)
) -> TaskHold:
    return await _written(
        session, task_reservations.claim_task(session, user.id, body.task_key, site=_site(), now=_now())
    )


@router.post("/release")
async def release_task(
    body: TaskKeyBody, user: User = Depends(contributor), session: AsyncSession = Depends(get_session)
) -> TaskHold:
    return await _written(
        session, task_reservations.release_task(session, user.id, body.task_key, now=_now())
    )


def _viewer(reader: User | None) -> Viewer:
    if reader is None:
        return Viewer()
    return Viewer(user_id=reader.id, review_role=role_value(reader))


async def _written(session: AsyncSession, change: Awaitable[TaskHold]) -> TaskHold:
    try:
        held = await change
    except Refused as refused:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, refused.message) from refused
    except InvalidInput as invalid:
        await session.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(invalid)) from invalid
    await session.commit()
    return held


def _site() -> str:
    return get_settings().public_web_url.rstrip("/")


def _now() -> datetime:
    return datetime.now(UTC)
