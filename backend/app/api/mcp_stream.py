from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Awaitable, Mapping
from types import MappingProxyType
from typing import Any

__all__ = [
    "EVENT_STREAM",
    "HEARTBEAT_FRAME",
    "OPENING_FRAME",
    "PROGRESS_METHOD",
    "STREAM_HEADERS",
    "STREAM_HEARTBEAT_SECONDS",
    "accepts_event_stream",
    "message_frame",
    "progress_frame",
    "progress_token",
    "reply_stream",
    "streams",
]

EVENT_STREAM = "text/event-stream"
STREAM_HEARTBEAT_SECONDS = 15.0
STREAM_HEADERS: Mapping[str, str] = MappingProxyType(
    {"Cache-Control": "no-store, no-transform", "X-Accel-Buffering": "no"}
)
OPENING_FRAME = ": stream open\n\n"
HEARTBEAT_FRAME = ": still working\n\n"
PROGRESS_METHOD = "notifications/progress"
TOOL_CALL = "tools/call"
PROGRESS_MESSAGE = "Still working: {seconds} seconds so far."


def accepts_event_stream(accept: str | None) -> bool:
    for part in (accept or "").split(","):
        media, *parameters = (piece.strip() for piece in part.split(";"))
        if media.lower() == EVENT_STREAM and not _refused(parameters):
            return True
    return False


def streams(accept: str | None, message: Any) -> bool:
    is_call = isinstance(message, dict) and message.get("method") == TOOL_CALL and "id" in message
    return is_call and accepts_event_stream(accept)


def progress_token(message: Any) -> str | int | None:
    params = message.get("params") if isinstance(message, dict) else None
    meta = params.get("_meta") if isinstance(params, dict) else None
    token = meta.get("progressToken") if isinstance(meta, dict) else None
    if isinstance(token, bool) or not isinstance(token, str | int):
        return None
    return token


def progress_frame(token: str | int, beat: int, heartbeat_seconds: float) -> str:
    seconds = round(beat * heartbeat_seconds)
    params = {"progressToken": token, "progress": beat, "message": PROGRESS_MESSAGE.format(seconds=seconds)}
    return message_frame({"jsonrpc": "2.0", "method": PROGRESS_METHOD, "params": params})


def message_frame(message: dict[str, Any]) -> str:
    return f"event: message\ndata: {json.dumps(message, ensure_ascii=False, separators=(',', ':'))}\n\n"


async def reply_stream(
    work: Awaitable[dict[str, Any] | None],
    token: str | int | None,
    *,
    heartbeat_seconds: float = STREAM_HEARTBEAT_SECONDS,
) -> AsyncIterator[str]:
    task = asyncio.ensure_future(work)
    try:
        yield OPENING_FRAME
        beat = 0
        while not task.done():
            await asyncio.wait({task}, timeout=heartbeat_seconds)
            if task.done():
                break
            beat += 1
            yield HEARTBEAT_FRAME if token is None else progress_frame(token, beat, heartbeat_seconds)
        reply = task.result()
        if reply is not None:
            yield message_frame(reply)
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


def _refused(parameters: list[str]) -> bool:
    for parameter in parameters:
        name, _, value = parameter.partition("=")
        if name.strip().lower() == "q":
            try:
                return float(value.strip()) <= 0
            except ValueError:
                return True
    return False
