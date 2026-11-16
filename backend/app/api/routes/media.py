from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.media_deps import media_deps
from app.core.deps import get_current_user
from app.media.jobs import MediaDeps, MediaRefused, media_options, submit_job, visible_job
from app.models import User
from app.schemas.media import MediaJobRequest

router = APIRouter(prefix="/media", tags=["media"])

REFUSAL_STATUS = {
    "capability": status.HTTP_403_FORBIDDEN,
    "not_found": status.HTTP_404_NOT_FOUND,
    "unshared": status.HTTP_404_NOT_FOUND,
    "too_few_claims": status.HTTP_409_CONFLICT,
    "key_conflict": status.HTTP_409_CONFLICT,
    "no_units": status.HTTP_429_TOO_MANY_REQUESTS,
    "busy": status.HTTP_429_TOO_MANY_REQUESTS,
    "budget": status.HTTP_503_SERVICE_UNAVAILABLE,
    "not_configured": status.HTTP_503_SERVICE_UNAVAILABLE,
}


def refusal(error: MediaRefused) -> HTTPException:
    headers = {"Retry-After": str(error.retry_after)} if error.retry_after else None
    return HTTPException(REFUSAL_STATUS[error.reason], error.message, headers)


@router.get("/options")
async def options(
    craftSlug: str = Query(min_length=1, max_length=200),
    user: User = Depends(get_current_user),
    deps: MediaDeps = Depends(media_deps),
) -> dict[str, Any]:
    try:
        found = await media_options(deps, user, craftSlug)
    except MediaRefused as error:
        raise refusal(error) from None
    return found.model_dump(mode="json", by_alias=True)


@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    payload: MediaJobRequest,
    response: Response,
    user: User = Depends(get_current_user),
    deps: MediaDeps = Depends(media_deps),
) -> dict[str, Any]:
    try:
        view, created = await submit_job(deps, user, payload)
    except MediaRefused as error:
        raise refusal(error) from None
    response.status_code = status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK
    return view.model_dump(mode="json", by_alias=True)


@router.get("/jobs/{job_id}")
async def read_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    deps: MediaDeps = Depends(media_deps),
) -> dict[str, Any]:
    try:
        view = await visible_job(deps, user, job_id)
    except MediaRefused as error:
        raise refusal(error) from None
    return view.model_dump(mode="json", by_alias=True)
