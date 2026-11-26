from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "ALLOWED_TOOLS",
    "EFFORT",
    "MAX_TOKENS",
    "MCP_BETA",
    "SERVER_NAME",
    "RunSettings",
    "craft_name",
    "mcp_server",
    "send_turn",
    "system_prompt",
    "toolset",
    "turn_params",
    "user_turn",
]

SERVER_NAME = "kalavigyan"
MCP_BETA = "mcp-client-2026-09-15"
MAX_TOKENS = 64_000
EFFORT = "high"
READING = ("find_crafts", "get_page", "get_facts", "list_components")
SOURCES = ("search_sources", "read_source", "lookup")
WORK = ("list_open_work", "my_work", "get_proposal")
STUDIO = ("edit_draft", "compose_component", "preview_page")
ALLOWED_TOOLS = frozenset((*READING, *SOURCES, *WORK, *STUDIO))
CLIENT_LINE = (
    "You are Claude, connected to the KalaVigyan MCP server at {server} with a contributor's account."
)
SERVER_HEADING = "Instructions from the KalaVigyan server:"
LIMITS = (
    "You may build drafts and previews. Do not propose, publish or review anything: never call propose_page "
    "or any proposing, publishing or review tool. Those tools are not offered in this connection."
)
REQUEST_LINE = "{request}\n\nThe craft: {name}."


@dataclass(frozen=True)
class RunSettings:
    model: str
    server_url: str
    system: str


def craft_name(slug: str) -> str:
    name = " ".join(slug.replace("-", " ").split())
    if not name:
        raise ValueError("name a craft by its slug, for example Sanganeri-Hand-Block-Printing")
    return name


def user_turn(request: str, craft: str) -> str:
    asked = request.strip()
    if not asked:
        raise ValueError("give the request a contributor types, for example: Deepen this craft's page.")
    return REQUEST_LINE.format(request=asked, name=craft_name(craft))


def system_prompt(server_url: str, instructions: str) -> str:
    parts: Sequence[str] = (
        CLIENT_LINE.format(server=server_url),
        f"{SERVER_HEADING}\n{instructions.strip()}" if instructions.strip() else "",
        LIMITS,
    )
    return "\n\n".join(part for part in parts if part)


def toolset() -> dict[str, Any]:
    return {
        "type": "mcp_toolset",
        "mcp_server_name": SERVER_NAME,
        "default_config": {"enabled": False},
        "configs": {name: {"enabled": True} for name in sorted(ALLOWED_TOOLS)},
    }


def mcp_server(url: str, token: str) -> dict[str, Any]:
    return {"type": "url", "url": url, "name": SERVER_NAME, "authorization_token": token}


def turn_params(settings: RunSettings, token: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": settings.model,
        "max_tokens": MAX_TOKENS,
        "betas": [MCP_BETA],
        "system": settings.system,
        "messages": messages,
        "mcp_servers": [mcp_server(settings.server_url, token)],
        "tools": [toolset()],
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": {"effort": EFFORT},
        "cache_control": {"type": "ephemeral"},
    }


def send_turn(
    client: Any, settings: RunSettings, token: Callable[[], str], messages: list[dict[str, Any]]
) -> Any:
    with client.beta.messages.stream(**turn_params(settings, token(), messages)) as stream:
        return stream.get_final_message()
