from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import public_reader
from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import InvalidInput
from app.services.knowledge_export import craft_export

router = APIRouter(tags=["knowledge"])


@router.get("/knowledge/crafts/{slug}/export", dependencies=[Depends(public_reader)])
async def export_craft(slug: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    site = get_settings().public_web_url.rstrip("/")
    try:
        exported = await craft_export(session, slug, site=site, now=datetime.now(UTC))
    except InvalidInput as unknown:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(unknown)) from unknown
    return exported.model_dump(mode="json", by_alias=True)
