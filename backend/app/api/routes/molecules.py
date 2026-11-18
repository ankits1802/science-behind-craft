from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import public_asset_reader, read_headers, unchanged_read
from app.core.db import get_session, release_connection, sessionmaker
from app.core.errors import AppError
from app.models import User
from app.services.live_sources import LiveSourcesStore
from app.services.molecule_conformers import CONFORMER_TYPE, ConformerCache, live_pubchem, stored_compound_cid
from app.services.object_store import media_bucket

router = APIRouter(prefix="/molecules", tags=["molecules"])
logger = logging.getLogger(__name__)

NO_CONFORMER_DETAIL = "There is no 3D structure for that compound."
UNAVAILABLE_DETAIL = "The 3D structure isn't available right now. Try again later."
PUBCHEM_CID_MAX = 10**12 - 1


async def conformer_cache(live: LiveSourcesStore) -> ConformerCache:
    objects = media_bucket()
    if objects is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL)
    try:
        source = await live_pubchem(live, sessionmaker())
    except AppError as error:
        logger.warning("the PubChem adapter could not be built: %s", error)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from None
    return ConformerCache(objects=objects, source=source)


@router.get("/{pubchem_cid}/conformer")
async def conformer(
    request: Request,
    pubchem_cid: int = Path(ge=1, le=PUBCHEM_CID_MAX),
    *,
    reader: User | None = Depends(public_asset_reader),
    session: AsyncSession = Depends(get_session),
) -> Response:
    stored = await stored_compound_cid(session, pubchem_cid)
    await release_connection(session)
    if not stored:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_CONFORMER_DETAIL)
    cache = await conformer_cache(request.app.state.live_sources)
    try:
        sdf = await cache.conformer(pubchem_cid)
    except AppError as error:
        logger.warning("the 3D conformer of CID %s could not be served: %s", pubchem_cid, error)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, UNAVAILABLE_DETAIL) from None
    if sdf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_CONFORMER_DETAIL)
    version = hashlib.sha256(sdf.encode("utf-8")).hexdigest()
    unchanged = unchanged_read(request, reader, version)
    if unchanged is not None:
        return unchanged
    return Response(sdf, media_type=CONFORMER_TYPE, headers=read_headers(reader, version))
