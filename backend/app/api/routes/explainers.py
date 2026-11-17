from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import User
from app.research.explainer_versions import ExplainerVersionDocument
from app.services.explainer_history import (
    UNKNOWN_EXPLAINER_DETAIL,
    UnknownExplainer,
    explainer_history,
    explainer_version,
    latest_version,
    mark_seen,
)

router = APIRouter(prefix="/explainers", tags=["explainers"])


@router.get("/{explainer_id}")
async def latest_explainer(
    explainer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        document = await latest_version(session, explainer_id, user.id)
    except UnknownExplainer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, UNKNOWN_EXPLAINER_DETAIL) from None
    return await _opened(session, user, document)


@router.get("/{explainer_id}/versions")
async def explainer_versions(
    explainer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        history = await explainer_history(session, explainer_id, user.id)
    except UnknownExplainer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, UNKNOWN_EXPLAINER_DETAIL) from None
    return history.model_dump(mode="json", by_alias=True)


@router.get("/{explainer_id}/versions/{version}")
async def explainer_at_version(
    explainer_id: uuid.UUID,
    version: int = Path(ge=1),
    *,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        document = await explainer_version(session, explainer_id, user.id, version)
    except UnknownExplainer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, UNKNOWN_EXPLAINER_DETAIL) from None
    return await _opened(session, user, document)


async def _opened(session: AsyncSession, user: User, document: ExplainerVersionDocument) -> dict[str, Any]:
    await mark_seen(session, user.id, document.mark.explainer_id, document.mark.version)
    await session.commit()
    return document.model_dump(mode="json", by_alias=True)
