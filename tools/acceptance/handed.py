from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from .pictures import Picture, reply_pictures

__all__ = [
    "HARNESS_USE",
    "STRIPPED",
    "HandedCall",
    "client_tool",
    "harness_uses",
    "run_handed",
    "stripped_texts",
]

HARNESS_USE = "tool_use"
STRIPPED = (
    "{count} pictures of this preview were kept by the run as files and not sent to you; the report above "
    "names each one and its drawing checks."
)

CallTool = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class HandedCall:
    turn: int
    call_id: str
    name: str
    arguments: dict[str, Any]
    texts: tuple[str, ...]
    is_error: bool
    pictures: tuple[Picture, ...] = ()
    structured: dict[str, Any] | None = None
    chars: int = 0

    def block(self) -> dict[str, Any]:
        content = [{"type": "text", "text": said} for said in self.texts]
        return {
            "type": "tool_result",
            "tool_use_id": self.call_id,
            "content": content,
            "is_error": self.is_error,
        }


def client_tool(listed: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": listed["name"],
        "description": listed["description"],
        "input_schema": listed["inputSchema"],
        "eager_input_streaming": True,
    }


def harness_uses(message: dict[str, Any]) -> list[dict[str, Any]]:
    return [block for block in message.get("content") or [] if block.get("type") == HARNESS_USE]


def stripped_texts(content: Sequence[dict[str, Any]]) -> tuple[str, ...]:
    texts = [str(item.get("text", "")) for item in content if item.get("type") == "text"]
    pictures = sum(1 for item in content if item.get("type") == "image")
    return tuple([*texts, STRIPPED.format(count=pictures)] if pictures else texts)


def run_handed(
    call_tool: CallTool, failures: tuple[type[Exception], ...], turn: int, block: dict[str, Any]
) -> HandedCall:
    name, arguments = str(block.get("name")), dict(block.get("input") or {})
    asked = {"turn": turn, "call_id": str(block.get("id")), "name": name, "arguments": arguments}
    try:
        result = call_tool(name, arguments)
    except failures as failed:
        said = f"The run could not call {name}: {type(failed).__name__}: {failed}"
        return HandedCall(**asked, texts=(said,), is_error=True, chars=len(said))
    content = result.get("content") or []
    texts = stripped_texts(content)
    pictures = () if result.get("isError") else tuple(reply_pictures(content))
    return HandedCall(
        **asked,
        texts=texts,
        is_error=bool(result.get("isError")),
        pictures=pictures,
        structured=result.get("structuredContent"),
        chars=sum(len(said) for said in texts),
    )
