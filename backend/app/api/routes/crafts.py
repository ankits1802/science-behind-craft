from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.http_cache import PRIVATE_NO_CACHE, revalidated
from app.core.roles import PROFESSOR, has_rank
from app.geo.region_view import craft_region
from app.models import Craft, User
from app.science.process_view import craft_process
from app.services import craft_catalogue, knowledge_view
from app.services.answering import NOT_FOUND_DETAIL
from app.services.craft_process import process_records
from app.services.region_records import region_records

router = APIRouter(prefix="/crafts", tags=["crafts"])

INACTIVE_REFUSAL = "The full craft list, with retired crafts, is for professors and above."


@router.get("/catalogue")
async def get_craft_catalogue(
    request: Request,
    response: Response,
    includeInactive: bool = False,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    if includeInactive and not has_rank(user, PROFESSOR):
        raise HTTPException(status.HTTP_403_FORBIDDEN, INACTIVE_REFUSAL)
    catalogue = await craft_catalogue.load_catalogue(session, include_inactive=includeInactive)
    not_modified = revalidated(request, response, catalogue["version"])
    return catalogue if not_modified is None else not_modified


@router.get("/{slug}/process")
async def get_craft_process(
    slug: str,
    response: Response,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    process = craft_process(await process_records(session, await _known_craft(session, slug)))
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return process.model_dump(mode="json", by_alias=True)


@router.get("/{slug}/region")
async def get_craft_region(
    slug: str,
    response: Response,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    region = craft_region(await region_records(session, await _known_craft(session, slug)))
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return region.model_dump(mode="json", by_alias=True)


async def _known_craft(session: AsyncSession, slug: str) -> Craft:
    craft = await knowledge_view.resolve_craft(session, slug)
    if craft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    return craft
