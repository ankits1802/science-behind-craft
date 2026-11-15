from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.roles import PROFESSOR, has_rank
from app.models import User
from app.services import craft_catalogue

router = APIRouter(prefix="/crafts", tags=["crafts"])

INACTIVE_REFUSAL = "The full craft list, with retired crafts, is for professors and the master admin."


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
    etag = craft_catalogue.quoted_etag(catalogue["version"])
    headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
    if craft_catalogue.etag_matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    response.headers.update(headers)
    return catalogue
