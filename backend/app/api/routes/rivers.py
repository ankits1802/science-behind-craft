from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session, release_connection
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.http_cache import not_modified, revalidation_headers
from app.models import User
from app.services.object_store import media_bucket
from app.services.river_store import basin_file
from app.services.river_topology import TOPOLOGY_TYPE, TopologyCache, basin_topology

router = APIRouter(prefix="/rivers", tags=["rivers"])
logger = logging.getLogger(__name__)

NO_RIVER_DETAIL = "There is no river by that id."
UNAVAILABLE_DETAIL = "Rivers aren't available right now. Try again later."
REACH_ID_MAX = 99_999_999


def river_topologies(request: Request) -> TopologyCache:
    cache: TopologyCache = request.app.state.river_topologies
    return cache


@router.get("/{main_riv}")
async def river_basin(
    request: Request,
    main_riv: int = Path(ge=1, le=REACH_ID_MAX),
    *,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    cache: TopologyCache = Depends(river_topologies),
) -> Response:
    basin = await basin_file(session, main_riv)
    await release_connection(session)
    if basin is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_RIVER_DETAIL)
    answered = not_modified(request, basin.sha256)
    if answered is not None:
        return answered
    objects = media_bucket()
    if objects is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL)
    try:
        found = await basin_topology(objects, cache, basin)
    except AppError as error:
        logger.warning("the topology of river %s could not be read: %s", main_riv, error)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from None
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_RIVER_DETAIL)
    return Response(found.body, media_type=TOPOLOGY_TYPE, headers=revalidation_headers(found.sha256))
