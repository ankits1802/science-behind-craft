from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import public_reader
from app.core.db import get_session
from app.core.http_cache import body_version, not_modified, revalidation_headers
from app.models import User
from app.research.public_summary import PublicSummary
from app.services.public_summary import SUMMARY_CACHE_SECONDS, SummaryCache, public_summary, summary_records

router = APIRouter(prefix="/public", tags=["public"])

SUMMARY_CACHE_CONTROL = f"public, max-age={SUMMARY_CACHE_SECONDS}"


def summary_cache(request: Request) -> SummaryCache:
    cache: SummaryCache = request.app.state.public_summary
    return cache


@router.get("/summary")
async def get_public_summary(
    request: Request,
    response: Response,
    _: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
    cache: SummaryCache = Depends(summary_cache),
) -> Any:
    async def built() -> PublicSummary:
        return public_summary(await summary_records(session))

    body = (await cache.summary(built)).model_dump(mode="json", by_alias=True)
    version = body_version(body)
    unchanged = not_modified(request, version, cache_control=SUMMARY_CACHE_CONTROL)
    if unchanged is not None:
        return unchanged
    response.headers.update(revalidation_headers(version, cache_control=SUMMARY_CACHE_CONTROL))
    return body
