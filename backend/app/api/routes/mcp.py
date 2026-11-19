from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mcp_auth import mcp_caller, record_call, scope_challenge
from app.api.mcp_protocol import PARSE_ERROR, error_reply, supported_version
from app.api.mcp_tools import ToolContext, answer
from app.api.oauth_hosts import MCP_ROUTE
from app.core.config import Settings, get_settings
from app.core.db import get_session

router = APIRouter(tags=["mcp"])

MCP_PATH = MCP_ROUTE
VERSION_HEADER = "mcp-protocol-version"
NOT_ENABLED = "The KalaVigyan MCP server is not switched on."
FOREIGN_ORIGIN = "This web origin may not call the KalaVigyan MCP server."
UNKNOWN_VERSION = "This MCP protocol version is not supported; initialize again."
UNREADABLE = "The body is not JSON."


def mcp_enabled() -> None:
    if not get_settings().mcp_server_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_ENABLED)


@router.post(MCP_PATH, dependencies=[Depends(mcp_enabled)])
async def mcp_message(request: Request, session: AsyncSession = Depends(get_session)) -> Response:
    settings = get_settings()
    _check_origin(request, settings)
    _check_version(request)
    caller = await mcp_caller(request, session)
    try:
        message = json.loads(await request.body())
    except ValueError:
        return JSONResponse(
            error_reply(None, PARSE_ERROR, UNREADABLE), status_code=status.HTTP_400_BAD_REQUEST
        )
    challenge = scope_challenge(message, caller)
    if challenge is not None:
        return challenge
    context = ToolContext(
        session=session,
        index=request.app.state.craft_index,
        site=settings.public_web_url.rstrip("/"),
        user=None if caller is None else caller.user,
        scopes=frozenset() if caller is None else caller.scopes,
    )
    reply = await answer(message, context)
    if caller is not None:
        await record_call(session, caller, message, reply)
    if reply is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return JSONResponse(reply)


def _check_origin(request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin")
    if origin is not None and origin.rstrip("/") not in settings.cors_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, FOREIGN_ORIGIN)


def _check_version(request: Request) -> None:
    version = request.headers.get(VERSION_HEADER)
    if version is not None and not supported_version(version):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, UNKNOWN_VERSION)
