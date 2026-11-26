import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import public_asset_reader
from app.core.db import get_session, release_connection
from app.core.errors import AppError, NotConfigured
from app.models import User
from app.services.answering import NOT_FOUND_DETAIL
from app.services.clip_stills import STILL_MIME, clip_still
from app.services.coded_clips import SharedClip, shared_clip
from app.services.craft_ai_media import page_media_key_of
from app.services.naming import content_disposition
from app.services.object_store import PresignedGet, media_bucket

router = APIRouter(prefix="/crafts", tags=["crafts"])

PAGE_MEDIA_LINK_SECONDS = 900
CLIP_LINK_SECONDS = 300
NO_MEDIA = "AI pictures and clips are not available right now."
NO_STILL = "No still of this clip can be shown."
STILL_CACHE = "private, max-age=300"
NO_STORE = {"Cache-Control": "no-store"}
NO_SNIFF = {"X-Content-Type-Options": "nosniff"}


@router.get("/media/{asset_id}")
async def get_page_media(
    asset_id: uuid.UUID,
    reader: User | None = Depends(public_asset_reader),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    key = await page_media_key_of(session, asset_id)
    await release_connection(session)
    if key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    link = _signed(key, PAGE_MEDIA_LINK_SECONDS)
    return RedirectResponse(
        link.url, status.HTTP_302_FOUND, headers={"Cache-Control": "private, max-age=300"}
    )


@router.get("/media/{asset_id}/film")
async def get_clip_link(
    asset_id: uuid.UUID,
    response: Response,
    reader: User | None = Depends(public_asset_reader),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    clip = await _clip(session, asset_id)
    link = _signed(clip.page_key, CLIP_LINK_SECONDS)
    response.headers.update(NO_STORE)
    return {"url": link.url, "expiresAt": link.expires_at.isoformat()}


@router.get("/media/{asset_id}/still")
async def get_clip_still(
    asset_id: uuid.UUID,
    reader: User | None = Depends(public_asset_reader),
    session: AsyncSession = Depends(get_session),
) -> Response:
    clip = await _clip(session, asset_id)
    bucket = media_bucket()
    if bucket is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NO_MEDIA)
    try:
        still = await clip_still(bucket, clip)
    except AppError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NO_MEDIA) from None
    if still is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_STILL)
    return Response(still, media_type=STILL_MIME, headers={"Cache-Control": STILL_CACHE, **NO_SNIFF})


async def _clip(session: AsyncSession, asset_id: uuid.UUID) -> SharedClip:
    clip = await shared_clip(session, asset_id)
    await release_connection(session)
    if clip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    return clip


def _signed(key: str, seconds: int) -> PresignedGet:
    bucket = media_bucket()
    if bucket is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NO_MEDIA)
    try:
        return bucket.presigned_get(
            key,
            disposition=content_disposition(key.rsplit("/", 1)[-1], inline=True),
            seconds=seconds,
            now=datetime.now(UTC),
        )
    except NotConfigured:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NO_MEDIA) from None
