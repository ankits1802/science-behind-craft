from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import cached_read, public_asset_reader, public_reader
from app.core.db import get_session
from app.geo.layers import LAYERS_BY_ID, map_layer, map_layer_list
from app.models import User
from app.services.map_layer_store import layer_values, listed_layers

router = APIRouter(prefix="/map", tags=["map"])

NO_LAYERS_DETAIL = "No map layers are stored yet."
NO_LAYER_DETAIL = "There is no map layer by that name."


@router.get("/layers")
async def get_map_layers(
    request: Request,
    response: Response,
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
) -> Any:
    listing = await listed_layers(session)
    if listing.boundary is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_LAYERS_DETAIL)
    return cached_read(
        request, response, reader, map_layer_list(listing).model_dump(mode="json", by_alias=True)
    )


@router.get("/layers/{layer}")
async def get_map_layer(
    layer: str,
    request: Request,
    response: Response,
    reader: User | None = Depends(public_asset_reader),
    session: AsyncSession = Depends(get_session),
) -> Any:
    spec = LAYERS_BY_ID.get(layer)
    stored = None if spec is None else await layer_values(session, spec)
    if stored is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_LAYER_DETAIL)
    body = map_layer(stored)
    return cached_read(
        request, response, reader, body.model_dump(mode="json", by_alias=True), version=body.version
    )
