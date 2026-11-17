from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require
from app.core.roles import Capability
from app.models import User
from app.services.explainer_history import UNKNOWN_EXPLAINER_DETAIL, UnknownExplainer
from app.services.saved_explainers import (
    SAVED_FULL_DETAIL,
    SavedFull,
    save_explainer,
    saved_explainers,
    unsave_explainer,
)

router = APIRouter(prefix="/saved-explainers", tags=["saved explainers"])

NOT_SAVED_DETAIL = "That explainer is not saved."


@router.get("")
async def saved(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    return (await saved_explainers(session, user.id)).model_dump(mode="json", by_alias=True)


@router.put("/{explainer_id}")
async def save(
    explainer_id: uuid.UUID,
    user: User = Depends(require(Capability.SAVE_EXPORT)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        kept = await save_explainer(session, user.id, explainer_id)
    except UnknownExplainer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, UNKNOWN_EXPLAINER_DETAIL) from None
    except SavedFull:
        raise HTTPException(status.HTTP_409_CONFLICT, SAVED_FULL_DETAIL) from None
    await session.commit()
    return kept.model_dump(mode="json", by_alias=True)


@router.delete("/{explainer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unsave(
    explainer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if not await unsave_explainer(session, user.id, explainer_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_SAVED_DETAIL)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
