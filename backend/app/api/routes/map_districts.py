from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import cached_read, public_reader, reading_acls
from app.core.db import get_session
from app.geo.district_view import district_crafts
from app.models import User
from app.services.district_crafts import district_records

router = APIRouter(prefix="/map", tags=["map"])

NO_DISTRICT_DETAIL = "There is no district by that code on the map."


@router.get("/districts/{district_lgd}")
async def get_district_crafts(
    request: Request,
    response: Response,
    district_lgd: int = Path(ge=1),
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
) -> Any:
    records = await district_records(session, district_lgd, acls=reading_acls(reader))
    if records is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_DISTRICT_DETAIL)
    return cached_read(
        request, response, reader, district_crafts(records).model_dump(mode="json", by_alias=True)
    )
