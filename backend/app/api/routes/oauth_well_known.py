from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.oauth_hosts import (
    AUTHORIZATION_SERVER_PATH,
    MCP_RESOURCE_PATH,
    PROTECTED_RESOURCE_PATH,
    configured_endpoints,
)
from app.api.routes.mcp import mcp_enabled
from app.research.oauth_metadata import authorization_server_metadata, protected_resource_metadata

router = APIRouter(tags=["oauth"], dependencies=[Depends(mcp_enabled)])

METADATA_HEADERS = {"Cache-Control": "public, max-age=300", "Access-Control-Allow-Origin": "*"}


@router.get(f"{PROTECTED_RESOURCE_PATH}{MCP_RESOURCE_PATH}")
@router.get(PROTECTED_RESOURCE_PATH)
async def protected_resource() -> JSONResponse:
    return JSONResponse(protected_resource_metadata(configured_endpoints()), headers=METADATA_HEADERS)


@router.get(AUTHORIZATION_SERVER_PATH)
async def authorization_server() -> JSONResponse:
    return JSONResponse(authorization_server_metadata(configured_endpoints()), headers=METADATA_HEADERS)
