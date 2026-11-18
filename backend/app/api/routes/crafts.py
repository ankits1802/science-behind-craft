from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import cached_read, public_reader, reading_acls, reading_role
from app.core.db import get_session
from app.core.deps import SIGN_IN_DETAIL
from app.core.kept_value import KeptValue
from app.core.roles import PROFESSOR, Capability, can, has_rank
from app.geo.region_view import craft_region
from app.models import Craft, User
from app.research.craft_page import without_evidence
from app.science.process_view import craft_process
from app.services import craft_catalogue, knowledge_view
from app.services.answering import NOT_FOUND_DETAIL
from app.services.craft_page import craft_page
from app.services.craft_page_records import craft_page_records
from app.services.craft_process import process_records
from app.services.region_records import region_records

router = APIRouter(prefix="/crafts", tags=["crafts"])

INACTIVE_REFUSAL = "The full craft list, with retired crafts, is for professors and above."


def catalogue_cache(request: Request) -> KeptValue[dict[str, Any]]:
    kept: KeptValue[dict[str, Any]] = request.app.state.craft_catalogue
    return kept


@router.get("/catalogue")
async def get_craft_catalogue(
    request: Request,
    response: Response,
    includeInactive: bool = False,
    *,
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
    kept: KeptValue[dict[str, Any]] = Depends(catalogue_cache),
) -> Any:
    if includeInactive and reader is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, SIGN_IN_DETAIL)
    if includeInactive and not has_rank(reader, PROFESSOR):
        raise HTTPException(status.HTTP_403_FORBIDDEN, INACTIVE_REFUSAL)
    if includeInactive:
        catalogue = await craft_catalogue.load_catalogue(session, include_inactive=True)
    else:
        catalogue = await craft_catalogue.reader_catalogue(session, kept)
    return cached_read(request, response, reader, catalogue, version=catalogue["version"])


@router.get("/{slug}/process")
async def get_craft_process(
    slug: str,
    request: Request,
    response: Response,
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
) -> Any:
    craft = await _known_craft(session, slug)
    process = craft_process(await process_records(session, craft, acls=reading_acls(reader)))
    return cached_read(request, response, reader, process.model_dump(mode="json", by_alias=True))


@router.get("/{slug}/page")
async def get_craft_page(
    slug: str,
    request: Request,
    response: Response,
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
) -> Any:
    craft = await _known_craft(session, slug)
    page = craft_page(await craft_page_records(session, craft, acls=reading_acls(reader)))
    shown = page if can(reading_role(reader), Capability.READ_ALL_EVIDENCE) else without_evidence(page)
    return cached_read(request, response, reader, shown.model_dump(mode="json", by_alias=True))


@router.get("/{slug}/region")
async def get_craft_region(
    slug: str,
    request: Request,
    response: Response,
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
) -> Any:
    region = craft_region(await region_records(session, await _known_craft(session, slug)))
    return cached_read(request, response, reader, region.model_dump(mode="json", by_alias=True))


async def _known_craft(session: AsyncSession, slug: str) -> Craft:
    craft = await knowledge_view.resolve_craft(session, slug)
    if craft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    return craft
