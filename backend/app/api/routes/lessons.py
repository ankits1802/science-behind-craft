from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.export_deps import EXPORT_UNAVAILABLE_DETAIL, export_tools
from app.core.db import get_session, release_connection
from app.core.deps import require
from app.core.errors import ExternalFailure, NotConfigured
from app.core.http_cache import PRIVATE_NO_CACHE
from app.core.roles import Capability
from app.models import User
from app.research.lesson_builder import LessonNotBuildable, UnknownLessonSection
from app.research.lessons import LESSON_FORMATS, LessonRequest
from app.services.citation_dates import accessed_dates
from app.services.explainer_history import UNKNOWN_EXPLAINER_DETAIL, UnknownExplainer
from app.services.export_files import ExportTools, lesson_file_link
from app.services.lesson_packs import build_lesson, delete_lesson, lesson_list, lesson_of

router = APIRouter(prefix="/lessons", tags=["lessons"])
logger = logging.getLogger(__name__)

NO_LESSON_DETAIL = "No lesson has that address."

LessonFormat = Literal[*LESSON_FORMATS]


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_lesson(
    request: LessonRequest,
    user: User = Depends(require(Capability.BUILD_LESSONS)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        pack = await build_lesson(session, user.id, request, now=datetime.now(UTC))
    except UnknownExplainer, UnknownLessonSection:
        raise HTTPException(status.HTTP_404_NOT_FOUND, UNKNOWN_EXPLAINER_DETAIL) from None
    except LessonNotBuildable as refused:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, refused.detail) from None
    return pack.model_dump(mode="json", by_alias=True)


@router.get("")
async def get_lessons(
    response: Response,
    user: User = Depends(require(Capability.BUILD_LESSONS)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    listed = await lesson_list(session, user.id)
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return listed.model_dump(mode="json", by_alias=True)


@router.get("/{lesson_id}")
async def get_lesson(
    lesson_id: uuid.UUID,
    response: Response,
    user: User = Depends(require(Capability.BUILD_LESSONS)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    pack = await lesson_of(session, user.id, lesson_id)
    if pack is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_LESSON_DETAIL)
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return pack.model_dump(mode="json", by_alias=True)


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_lesson(
    lesson_id: uuid.UUID,
    user: User = Depends(require(Capability.BUILD_LESSONS)),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if not await delete_lesson(session, user.id, lesson_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_LESSON_DETAIL)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{lesson_id}/files/{fmt}")
async def get_lesson_file(
    lesson_id: uuid.UUID,
    fmt: LessonFormat,
    response: Response,
    *,
    user: User = Depends(require(Capability.BUILD_LESSONS)),
    session: AsyncSession = Depends(get_session),
    tools: ExportTools = Depends(export_tools),
) -> dict[str, Any]:
    pack = await lesson_of(session, user.id, lesson_id)
    if pack is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_LESSON_DETAIL)
    accessed = await accessed_dates(session, pack.sources)
    await release_connection(session)
    try:
        link = await lesson_file_link(tools, user.id, pack, accessed, fmt)
    except (ExternalFailure, NotConfigured) as error:
        logger.warning("lesson %s could not be filed as %s: %s", lesson_id, fmt, error)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, EXPORT_UNAVAILABLE_DETAIL) from None
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return link.model_dump(mode="json", by_alias=True)
