from __future__ import annotations

import json
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mcp_auth import SERVER_FAILED, mcp_caller, record_call, record_failed_call, scope_challenge
from app.api.mcp_cors import is_web_origin
from app.api.mcp_headers import VERSION_HEADER, modern_status, refused_up_front
from app.api.mcp_meta import is_modern
from app.api.mcp_protocol import (
    INTERNAL_ERROR,
    PARSE_ERROR,
    error_reply,
    supported_version,
    unsupported_version,
)
from app.api.mcp_stream import EVENT_STREAM, STREAM_HEADERS, progress_token, reply_stream, streams
from app.api.mcp_tools import ToolContext, answer, answered_whole
from app.api.oauth_hosts import MCP_ROUTE
from app.core.config import get_settings
from app.core.db import get_session, release_connection, sessionmaker
from app.core.shielded import ShieldedWork
from app.services.oauth_bearer import McpCaller

router = APIRouter(tags=["mcp"])
logger = logging.getLogger(__name__)

MCP_PATH = MCP_ROUTE
NOT_ENABLED = "The KalaVigyan MCP server is not switched on."
FOREIGN_ORIGIN = "This web origin may not call the KalaVigyan MCP server."
UNREADABLE = "The body is not JSON."
STREAMED_CALL = "mcp tools/call"

Sessions = Callable[[], AbstractAsyncContextManager[AsyncSession]]


def mcp_enabled() -> None:
    if not get_settings().mcp_server_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_ENABLED)


def stream_sessions() -> Sessions:
    return sessionmaker()


@router.post(MCP_PATH, dependencies=[Depends(mcp_enabled)])
async def mcp_message(
    request: Request,
    session: AsyncSession = Depends(get_session),
    sessions: Sessions = Depends(stream_sessions),
) -> Response:
    _check_origin(request)
    stale = _unknown_version(request)
    if stale is not None:
        return stale
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
    refused = refused_up_front(request.headers, message)
    if refused is not None:
        body = error_reply(message.get("id"), refused.code, refused.message, refused.data)
        return JSONResponse(body, status_code=status.HTTP_400_BAD_REQUEST)
    if streams(request.headers.get("accept"), message) and not answered_whole(message):
        await release_connection(session)
        return _streamed(request, message, caller, sessions)
    reply = await _answered(message, _context(request, caller, session, sessions), caller)
    if reply is None:
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return JSONResponse(reply, status_code=modern_status(reply) if is_modern(message) else status.HTTP_200_OK)


def _streamed(
    request: Request, message: Any, caller: McpCaller | None, sessions: Sessions
) -> StreamingResponse:
    shield: ShieldedWork = request.app.state.shielded_work
    work = shield.run(_answered_alone(request, message, caller, sessions), name=STREAMED_CALL)
    return StreamingResponse(
        reply_stream(work, progress_token(message)), media_type=EVENT_STREAM, headers=dict(STREAM_HEADERS)
    )


async def _answered_alone(
    request: Request, message: Any, caller: McpCaller | None, sessions: Sessions
) -> dict[str, Any] | None:
    try:
        async with sessions() as session:
            return await _answered(message, _context(request, caller, session, sessions), caller)
    except Exception:
        logger.exception("a streamed MCP call failed")
        return error_reply(message.get("id"), INTERNAL_ERROR, SERVER_FAILED)


async def _answered(message: Any, context: ToolContext, caller: McpCaller | None) -> dict[str, Any] | None:
    try:
        reply = await answer(message, context)
    except Exception:
        if caller is not None:
            await record_failed_call(context.session, caller, message)
        raise
    if caller is not None:
        await record_call(context.session, caller, message, reply)
    return reply


def _context(
    request: Request, caller: McpCaller | None, session: AsyncSession, sessions: Sessions
) -> ToolContext:
    return ToolContext(
        session=session,
        index=request.app.state.craft_index,
        site=get_settings().public_web_url.rstrip("/"),
        user=None if caller is None else caller.user,
        scopes=frozenset() if caller is None else caller.scopes,
        caller=caller,
        background=request.app.state.shielded_work,
        sessions=sessions,
        tasks=request.app.state.mcp_tasks,
    )


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is not None and not is_web_origin(origin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, FOREIGN_ORIGIN)


def _unknown_version(request: Request) -> JSONResponse | None:
    version = request.headers.get(VERSION_HEADER)
    if version is None or supported_version(version):
        return None
    refused = unsupported_version(version)
    body = error_reply(None, refused.code, refused.message, refused.data)
    return JSONResponse(body, status_code=status.HTTP_400_BAD_REQUEST)
