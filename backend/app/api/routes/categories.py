from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import cached_read, public_reader
from app.core.db import get_session
from app.models import User
from app.research.crafts import SLUG_MAX_CHARS
from app.services.category_page import category_list, category_page
from app.services.category_records import category_list_records, category_page_records

router = APIRouter(prefix="/categories", tags=["categories"])

CATEGORY_NOT_FOUND_DETAIL = "There is no craft category by that name."


@router.get("")
async def get_categories(
    request: Request,
    response: Response,
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
) -> Any:
    listing = category_list(await category_list_records(session))
    return cached_read(request, response, reader, listing.model_dump(mode="json", by_alias=True))


@router.get("/{slug}")
async def get_category(
    request: Request,
    response: Response,
    slug: str = Path(min_length=1, max_length=SLUG_MAX_CHARS),
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
) -> Any:
    records = await category_page_records(session, slug)
    if records is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, CATEGORY_NOT_FOUND_DETAIL)
    page = category_page(records)
    return cached_read(request, response, reader, page.model_dump(mode="json", by_alias=True))
