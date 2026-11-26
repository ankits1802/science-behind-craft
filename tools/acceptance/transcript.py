from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .loop import LoopOutcome, Turn

__all__ = [
    "TRANSCRIPT_SCHEMA_VERSION",
    "TRIM_CHARS",
    "Call",
    "RunFacts",
    "block_entry",
    "paired_calls",
    "result_texts",
    "transcript",
    "trimmed",
]

TRANSCRIPT_SCHEMA_VERSION = 1
TRIM_CHARS = 2_000
MORE = " [... {count} more characters]"


@dataclass(frozen=True)
class RunFacts:
    craft: str
    request: str
    model: str
    cap_usd: str


@dataclass(frozen=True)
class Call:
    turn: int
    call_id: str
    name: str
    arguments: dict[str, Any]
    texts: tuple[str, ...]
    other_content: tuple[str, ...]
    is_error: bool
    answered: bool


def trimmed(text: str, limit: int = TRIM_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + MORE.format(count=len(text) - limit)


def result_texts(block: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    content = block.get("content")
    if isinstance(content, str):
        return (content,), ()
    items = content or []
    texts = tuple(item.get("text", "") for item in items if item.get("type") == "text")
    others = tuple(str(item.get("type")) for item in items if item.get("type") != "text")
    return texts, others


def block_entry(block: dict[str, Any]) -> dict[str, Any]:
    kind = block.get("type")
    if kind == "text":
        return {"type": "text", "text": trimmed(block.get("text", ""))}
    if kind == "thinking":
        return {"type": "thinking", "summary": trimmed(block.get("thinking") or "")}
    if kind == "mcp_tool_use":
        arguments = json.dumps(block.get("input") or {}, ensure_ascii=False)
        return {
            "type": "call",
            "id": block.get("id"),
            "name": block.get("name"),
            "arguments": trimmed(arguments),
        }
    if kind == "mcp_tool_result":
        texts, others = result_texts(block)
        return {
            "type": "result",
            "callId": block.get("tool_use_id"),
            "isError": bool(block.get("is_error")),
            "text": trimmed("\n".join(texts)),
            "otherContent": list(others),
        }
    if kind == "mcp_tool_listing":
        names = [tool.get("name") for tool in block.get("tools") or []]
        return {"type": "listing", "server": block.get("mcp_server_name"), "tools": names}
    return {"type": kind}


def paired_calls(turns: Sequence[Turn]) -> list[Call]:
    results = {
        block.get("tool_use_id"): block
        for turn in turns
        for block in turn.message.get("content") or []
        if block.get("type") == "mcp_tool_result"
    }
    return [
        _call(turn.number, block, results.get(block.get("id")))
        for turn in turns
        for block in turn.message.get("content") or []
        if block.get("type") == "mcp_tool_use"
    ]


def transcript(facts: RunFacts, outcome: LoopOutcome) -> dict[str, Any]:
    return {
        "schemaVersion": TRANSCRIPT_SCHEMA_VERSION,
        "craft": facts.craft,
        "request": facts.request,
        "model": facts.model,
        "capUsd": facts.cap_usd,
        "stopped": outcome.stopped,
        "detail": outcome.detail,
        "trimmedAt": TRIM_CHARS,
        "turns": [_turn_entry(turn) for turn in outcome.turns],
    }


def _call(turn: int, used: dict[str, Any], result: dict[str, Any] | None) -> Call:
    texts, others = result_texts(result) if result is not None else ((), ())
    return Call(
        turn=turn,
        call_id=str(used.get("id")),
        name=str(used.get("name")),
        arguments=dict(used.get("input") or {}),
        texts=texts,
        other_content=others,
        is_error=bool(result.get("is_error")) if result is not None else False,
        answered=result is not None,
    )


def _turn_entry(turn: Turn) -> dict[str, Any]:
    return {
        "turn": turn.number,
        "stopReason": turn.message.get("stop_reason"),
        "costUsd": str(turn.cost),
        "usage": turn.message.get("usage"),
        "blocks": [block_entry(block) for block in turn.message.get("content") or []],
    }
