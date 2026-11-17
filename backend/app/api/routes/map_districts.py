from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.http_cache import PRIVATE_NO_CACHE
from app.geo.district_view import district_crafts
from app.models import User
from app.services.district_crafts import district_records

router = APIRouter(prefix="/map", tags=["map"])

NO_DISTRICT_DETAIL = "There is no district by that code on the map."


@router.get("/districts/{district_lgd}")
async def get_district_crafts(
    response: Response,
    district_lgd: int = Path(ge=1),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    records = await district_records(session, district_lgd)
    if records is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_DISTRICT_DETAIL)
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return district_crafts(records).model_dump(mode="json", by_alias=True)
