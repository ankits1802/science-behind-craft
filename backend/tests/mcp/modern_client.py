from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any

from app.api.mcp_tasks import McpTasks
from app.api.mcp_tools import ToolContext, answer
from app.services.craft_resolver import CraftIndexStore

VERSION = "2026-07-28"
SITE = "https://kalavigyan.example"
TASKS = {"extensions": {"io.modelcontextprotocol/tasks": {}}}
FORMS = {"elicitation": {"form": {}}}
FILES = {"extensions": {"io.modelcontextprotocol/files": {"upload": {}, "download": {}}}}
SKILLS = {"extensions": {"io.modelcontextprotocol/skills": {}}}


def modern(
    method: str,
    params: Mapping[str, Any] | None = None,
    *,
    capabilities: Mapping[str, Any] | None = None,
    request_id: int = 1,
) -> dict[str, Any]:
    meta = {
        "io.modelcontextprotocol/protocolVersion": VERSION,
        "io.modelcontextprotocol/clientInfo": {"name": "kalavigyan-tests", "version": "1"},
        "io.modelcontextprotocol/clientCapabilities": dict(capabilities or {}),
    }
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": {**(params or {}), "_meta": meta}}


def legacy(method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": 1, "method": method, "params": dict(params or {})}


def tool_call(name: str, arguments: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    return {"name": name, "arguments": dict(arguments), **extra}


def bare_context(**changes: Any) -> ToolContext:
    context = ToolContext(session=None, index=CraftIndexStore(), site=SITE)  # type: ignore[arg-type]
    return replace(context, **changes)


@asynccontextmanager
async def no_session() -> AsyncIterator[Any]:
    yield None


def with_tasks(context: ToolContext) -> ToolContext:
    return replace(context, tasks=McpTasks(), sessions=no_session)


async def result_of(message: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    reply = await answer(message, context)
    assert reply is not None and "result" in reply, reply
    return reply["result"]


async def error_of(message: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    reply = await answer(message, context)
    assert reply is not None and "error" in reply, reply
    return reply["error"]
