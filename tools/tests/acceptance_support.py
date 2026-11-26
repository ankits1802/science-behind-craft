from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from anthropic.types.beta import BetaMessage

from acceptance.costs import Prices
from acceptance.request import RunSettings

REPO = Path(__file__).resolve().parents[2]
SERVER_URL = "https://api.example/api/mcp"
TOKEN = "kvmcp_at_fixture-not-a-token"
SETTINGS = RunSettings(model="claude-opus-5-5", server_url=SERVER_URL, system="A contributor's client.")
PRICES = Prices("claude-opus-5-5", Decimal(4), Decimal(20))


def usage(plain: int = 0, output: int = 0, *, written: int = 0, read: int = 0) -> dict[str, int]:
    return {
        "input_tokens": plain,
        "output_tokens": output,
        "cache_creation_input_tokens": written,
        "cache_read_input_tokens": read,
    }


def text(said: str) -> dict[str, Any]:
    return {"type": "text", "text": said}


def call(call_id: str, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": "mcp_tool_use",
        "id": call_id,
        "name": name,
        "server_name": "kalavigyan",
        "input": arguments or {},
    }


def run_call(call_id: str, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "tool_use", "id": call_id, "name": name, "input": arguments or {}}


def result(call_id: str, texts: Sequence[str], *, is_error: bool = False) -> dict[str, Any]:
    content = [{"type": "text", "text": said} for said in texts]
    return {"type": "mcp_tool_result", "tool_use_id": call_id, "is_error": is_error, "content": content}


def message(
    stop_reason: str, content: Iterable[dict[str, Any]], spent: dict[str, int] | None = None
) -> BetaMessage:
    return BetaMessage.model_validate(
        {
            "id": "msg_fixture",
            "type": "message",
            "role": "assistant",
            "model": SETTINGS.model,
            "content": list(content),
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": spent or usage(),
        }
    )


class FakeApiError(Exception):
    pass


@dataclass
class FakeStream:
    reply: BetaMessage

    def __enter__(self) -> FakeStream:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get_final_message(self) -> BetaMessage:
        return self.reply


@dataclass
class FakeMessages:
    replies: list[BetaMessage | Exception]
    requests: list[dict[str, Any]] = field(default_factory=list)

    def stream(self, **params: Any) -> FakeStream:
        self.requests.append(params)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return FakeStream(reply)


class FakeClient:
    def __init__(self, replies: Sequence[BetaMessage | Exception]) -> None:
        self.messages = FakeMessages(list(replies))
        self.beta = SimpleNamespace(messages=self.messages)

    @property
    def requests(self) -> list[dict[str, Any]]:
        return self.messages.requests
