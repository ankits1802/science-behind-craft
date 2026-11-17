from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import User
from app.services.notifications import mark_all_read, mark_read, notification_list

router = APIRouter(prefix="/notifications", tags=["notifications"])

UNKNOWN_NOTE_DETAIL = "No note has that address."


@router.get("")
async def notifications(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    return (await notification_list(session, user.id)).model_dump(mode="json", by_alias=True)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> Response:
    await mark_all_read(session, user.id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if not await mark_read(session, user.id, notification_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, UNKNOWN_NOTE_DETAIL)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
