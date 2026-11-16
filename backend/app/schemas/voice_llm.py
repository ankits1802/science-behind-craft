from __future__ import annotations

import json
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "CONVERSATION_HEADER",
    "DONE_FRAME",
    "LLM_ERROR_CODES",
    "SYSTEM_TOOL_NAMES",
    "VOICE_LLM_MODEL",
    "VOICE_LLM_PATH",
    "LlmChatRequest",
    "LlmChoice",
    "LlmChunk",
    "LlmDelta",
    "LlmError",
    "LlmErrorBody",
    "LlmFunctionCall",
    "LlmMessage",
    "LlmToolCall",
    "llm_error_frame",
    "llm_frame",
]

VOICE_LLM_PATH = "/api/voice/llm/v1/chat/completions"
CONVERSATION_HEADER = "X-KV-Conversation-Id"
VOICE_LLM_MODEL = "kalavigyan-voice"
SYSTEM_TOOL_NAMES = ("end_call", "language_detection", "skip_turn")
LLM_ERROR_CODES = ("unauthorized", "bad_request", "unavailable")
DONE_FRAME = "data: [DONE]\n\n"


class _Inbound(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class _Outbound(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LlmMessage(_Inbound):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None


class LlmChatRequest(_Inbound):
    model: str = Field(min_length=1, max_length=200)
    messages: list[LlmMessage] = Field(min_length=1)
    stream: bool
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    tools: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _streamed_with_a_user_turn(self) -> Self:
        if not self.stream:
            raise ValueError("the voice model answers only as a stream")
        if not any(message.role == "user" for message in self.messages):
            raise ValueError("a voice turn carries at least one user message")
        return self


class LlmFunctionCall(_Outbound):
    name: str = Field(min_length=1, max_length=64)
    arguments: str

    @model_validator(mode="after")
    def _arguments_are_a_json_object(self) -> Self:
        if not isinstance(json.loads(self.arguments), dict):
            raise ValueError("tool arguments are a JSON object")
        return self


class LlmToolCall(_Outbound):
    index: int = Field(ge=0)
    id: str = Field(min_length=1, max_length=120)
    type: Literal["function"]
    function: LlmFunctionCall


class LlmDelta(_Outbound):
    role: Literal["assistant"] | None = None
    content: str | None = None
    tool_calls: list[LlmToolCall] | None = None


class LlmChoice(_Outbound):
    index: Literal[0]
    delta: LlmDelta
    finish_reason: Literal["stop", "tool_calls"] | None


class LlmChunk(_Outbound):
    id: str = Field(pattern=r"^chatcmpl-[0-9a-f]{32}$")
    object: Literal["chat.completion.chunk"]
    created: int = Field(ge=0)
    model: Literal[VOICE_LLM_MODEL]
    choices: list[LlmChoice] = Field(min_length=1, max_length=1)


class LlmErrorBody(_Outbound):
    message: str = Field(min_length=1)
    type: Literal["invalid_request_error", "server_error"]
    code: Literal[*LLM_ERROR_CODES]


class LlmError(_Outbound):
    error: LlmErrorBody


def llm_frame(chunk: LlmChunk) -> str:
    payload = chunk.model_dump(mode="json", exclude_unset=True)
    return f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


def llm_error_frame(error: LlmError) -> str:
    payload = error.model_dump(mode="json")
    return f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"
