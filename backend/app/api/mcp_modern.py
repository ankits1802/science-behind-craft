from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from app.core.config import get_settings

from .mcp_meta import FILES_EXTENSION, SERVER_INFO_KEY, SKILLS_EXTENSION, TASKS_EXTENSION, missing_capability
from .mcp_protocol import (
    INVALID_PARAMS,
    PROTOCOL_VERSIONS,
    RESOURCE_NOT_FOUND,
    SERVER_INSTRUCTIONS,
    RequestError,
    server_info,
)
from .mcp_skills import skill_get, skill_list
from .mcp_tasks import UNKNOWN, task_reply
from .mcp_tool_base import ToolContext

__all__ = [
    "CACHE_TTL_MS",
    "COMPLETE",
    "MODERN_METHODS",
    "completed",
    "discover_result",
    "modern_capabilities",
    "modern_code",
    "modern_method",
]

COMPLETE = "complete"
CACHE_TTL_MS = 300_000
PUBLIC, PRIVATE = "public", "private"
CACHED: Mapping[str, str] = MappingProxyType(
    {
        "server/discover": PUBLIC,
        "tools/list": PRIVATE,
        "prompts/list": PUBLIC,
        "resources/list": PUBLIC,
        "resources/templates/list": PUBLIC,
        "resources/read": PUBLIC,
        "skills/list": PUBLIC,
        "skills/get": PUBLIC,
    }
)
TASK_METHODS = frozenset({"tasks/get", "tasks/update", "tasks/cancel"})
MODERN_METHODS = frozenset({"server/discover", "skills/list", "skills/get", *TASK_METHODS})


def modern_capabilities() -> dict[str, Any]:
    extensions: dict[str, Any] = {SKILLS_EXTENSION: {}, TASKS_EXTENSION: {}}
    if get_settings().mcp_file_uploads_enabled:
        extensions[FILES_EXTENSION] = {"upload": {}}
    return {"tools": {}, "prompts": {}, "resources": {}, "extensions": extensions}


def discover_result() -> dict[str, Any]:
    return {
        "supportedVersions": list(PROTOCOL_VERSIONS),
        "capabilities": modern_capabilities(),
        "instructions": SERVER_INSTRUCTIONS,
    }


async def modern_method(method: str, params: Mapping[str, Any], context: ToolContext) -> dict[str, Any]:
    if method == "server/discover":
        return discover_result()
    if method == "skills/list":
        return skill_list()
    if method == "skills/get":
        return skill_get(params)
    return await _task_method(method, params, context)


def completed(method: str, result: Mapping[str, Any]) -> dict[str, Any]:
    shaped: dict[str, Any] = {"resultType": COMPLETE, **result}
    scope = CACHED.get(method)
    if scope is not None and shaped["resultType"] == COMPLETE:
        shaped |= {"ttlMs": CACHE_TTL_MS, "cacheScope": scope}
    given = result.get("_meta")
    held = dict(given) if isinstance(given, Mapping) else {}
    return shaped | {"_meta": {**held, SERVER_INFO_KEY: server_info()}}


def modern_code(code: int) -> int:
    return INVALID_PARAMS if code == RESOURCE_NOT_FOUND else code


async def _task_method(method: str, params: Mapping[str, Any], context: ToolContext) -> dict[str, Any]:
    meta = context.meta
    if meta is None or not meta.runs_tasks():
        raise missing_capability({"extensions": {TASKS_EXTENSION: {}}})
    tasks, principal = context.tasks, context.principal
    if tasks is None or principal is None:
        raise RequestError(INVALID_PARAMS, UNKNOWN)
    now = datetime.now(UTC)
    if method == "tasks/get":
        return task_reply(await tasks.get(principal, params.get("taskId"), now), COMPLETE)
    if method == "tasks/cancel":
        await tasks.cancel(principal, params.get("taskId"), now)
        return {}
    await tasks.get(principal, params.get("taskId"), now)
    return {}
