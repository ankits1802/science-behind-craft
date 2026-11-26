from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType
from typing import Any

from app.core.config import get_settings

from .mcp_ask_tools import ASK_TOOLS
from .mcp_calls import call_tool
from .mcp_check_tools import CHECK_TOOLS
from .mcp_compose_tools import COMPOSE_TOOLS
from .mcp_dataset_tools import DATASET_TOOLS
from .mcp_fact_tools import FACT_TOOLS
from .mcp_field_photo_tools import FIELD_PHOTO_TOOLS
from .mcp_gap_tools import GAP_TOOLS
from .mcp_guides import guide_read, guide_template, is_guide_uri
from .mcp_lookup_tools import LOOKUP_TOOLS
from .mcp_meta import RequestMeta, is_modern, request_meta
from .mcp_modern import MODERN_METHODS, completed, modern_code, modern_method
from .mcp_page_tools import PAGE_TOOLS
from .mcp_picture_tools import PICTURE_TOOLS
from .mcp_prompts import prompt_list, prompt_result
from .mcp_protocol import (
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    RequestError,
    error_reply,
    initialize_result,
    request_parts,
    result_reply,
)
from .mcp_read_tools import READ_TOOLS
from .mcp_report_tools import REPORT_TOOLS
from .mcp_resources import resource_list, resource_read, resource_templates
from .mcp_review_tools import REVIEW_TOOLS
from .mcp_skills import is_skill_uri, skill_read
from .mcp_source_tools import SOURCE_TOOLS
from .mcp_structure_tools import STRUCTURE_TOOLS
from .mcp_studio_sources import STUDIO_SOURCE_TOOLS
from .mcp_tool_base import Tool, ToolContext, listed_to
from .mcp_work_tools import WORK_TOOLS

__all__ = ["LONG_RUNNING", "TOOLS", "ToolContext", "answer", "answered_whole", "tool_list"]

LONG_RUNNING = frozenset(
    {
        "ask",
        "read_source",
        "search_sources",
        "edit_draft",
        "preview_page",
        "propose_page",
        "compose_component",
        "give_pictures",
    }
)
TOOLS: Mapping[str, Tool] = MappingProxyType(
    {
        tool.name: replace(tool, runs_long=tool.name in LONG_RUNNING)
        for tool in (
            *READ_TOOLS,
            *ASK_TOOLS,
            *LOOKUP_TOOLS,
            *STUDIO_SOURCE_TOOLS,
            *WORK_TOOLS,
            *GAP_TOOLS,
            *FACT_TOOLS,
            *STRUCTURE_TOOLS,
            *SOURCE_TOOLS,
            *DATASET_TOOLS,
            *PAGE_TOOLS,
            *COMPOSE_TOOLS,
            *PICTURE_TOOLS,
            *CHECK_TOOLS,
            *FIELD_PHOTO_TOOLS,
            *REVIEW_TOOLS,
            *REPORT_TOOLS,
        )
    }
)


def tool_list(scopes: frozenset[str] = frozenset(), *, with_files: bool = False) -> list[dict[str, Any]]:
    return [tool.listed(with_files=with_files) for tool in TOOLS.values() if listed_to(tool, scopes)]


def answered_whole(message: Any) -> bool:
    if not is_modern(message):
        return False
    params = message.get("params")
    tool = TOOLS.get(str(params.get("name"))) if isinstance(params, Mapping) else None
    return tool is not None and tool.files is not None


async def answer(message: Any, context: ToolContext) -> dict[str, Any] | None:
    try:
        request_id, method, params, notification = request_parts(message)
    except RequestError as refused:
        return error_reply(refused.request_id, refused.code, refused.message)
    if notification:
        return None
    modern = is_modern(message)
    try:
        meta = request_meta(method, params)
        if meta is None:
            return result_reply(request_id, await _dispatch(method, params, context))
        result = await _dispatch(method, params, replace(context, meta=meta))
        return result_reply(request_id, completed(method, result))
    except RequestError as refused:
        code = modern_code(refused.code) if modern else refused.code
        return error_reply(request_id, code, refused.message, refused.data)


async def _dispatch(method: str, params: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    if method == "initialize" and context.meta is None:
        return initialize_result(params)
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": tool_list(context.scopes, with_files=_lists_files(context.meta))}
    if method == "tools/call":
        return await _call(params, context)
    if context.meta is not None and method in MODERN_METHODS:
        return modern_method(method, params, context)
    return _catalogue(method, params, context)


def _catalogue(method: str, params: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    if method == "prompts/list":
        return prompt_list()
    if method == "prompts/get":
        return prompt_result(params)
    if method == "resources/list":
        return resource_list(context.site)
    if method == "resources/templates/list":
        return {"resourceTemplates": [*resource_templates()["resourceTemplates"], guide_template()]}
    if method == "resources/read":
        return _read(params)
    raise RequestError(METHOD_NOT_FOUND, f"the server offers no method {method}")


def _read(params: dict[str, Any]) -> dict[str, Any]:
    uri = params.get("uri")
    if is_skill_uri(uri):
        return skill_read(uri)
    return guide_read(uri) if is_guide_uri(uri) else resource_read(params)


async def _call(params: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    tool = TOOLS.get(str(params.get("name")))
    if tool is None:
        raise RequestError(INVALID_PARAMS, f"no tool is named {params.get('name')}; tools/list gives them")
    return await call_tool(tool, params, context)


def _lists_files(meta: RequestMeta | None) -> bool:
    return meta is not None and meta.uploads_files() and get_settings().mcp_file_uploads_enabled
