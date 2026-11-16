from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable
from dataclasses import dataclass
from typing import Literal

from app.schemas.voice_llm import (
    DONE_FRAME,
    VOICE_LLM_MODEL,
    LlmChoice,
    LlmChunk,
    LlmDelta,
    LlmError,
    LlmErrorBody,
    LlmFunctionCall,
    LlmToolCall,
    llm_error_frame,
    llm_frame,
)

from .phrases import FILLERS, phrase

__all__ = [
    "FILLER_AFTER_SECONDS",
    "UNAUTHORIZED_MESSAGE",
    "AgentReply",
    "EndCall",
    "error_body",
    "reply_stream",
]

logger = logging.getLogger(__name__)

FILLER_AFTER_SECONDS = 0.7
UNAUTHORIZED_MESSAGE = "This voice session is not allowed."
UNAVAILABLE_MESSAGE = "The answer could not be prepared just now."

FinishReason = Literal["stop", "tool_calls"] | None


@dataclass(frozen=True)
class EndCall:
    reason: str
    message: str


@dataclass(frozen=True)
class AgentReply:
    parts: tuple[str, ...] = ()
    end_call: EndCall | None = None


def error_body(code: str, message: str) -> LlmError:
    kind = "server_error" if code == "unavailable" else "invalid_request_error"
    return LlmError(error=LlmErrorBody(message=message, type=kind, code=code))


async def reply_stream(
    reply: Awaitable[AgentReply], *, turn_id: uuid.UUID, created: int, language: str
) -> AsyncIterator[str]:
    frames = _Frames(turn_id, created)
    task = asyncio.ensure_future(reply)
    try:
        done, _ = await asyncio.wait({task}, timeout=FILLER_AFTER_SECONDS)
        if not done:
            yield frames.content(phrase(FILLERS, language))
        answer = await task
    except Exception:
        logger.exception("voice turn failed after the stream started")
        yield llm_error_frame(error_body("unavailable", UNAVAILABLE_MESSAGE))
        yield DONE_FRAME
        return
    finally:
        if not task.done():
            task.cancel()
    for frame in frames.reply(answer):
        yield frame
    yield DONE_FRAME


class _Frames:
    def __init__(self, turn_id: uuid.UUID, created: int) -> None:
        self._id = f"chatcmpl-{turn_id.hex}"
        self._created = created
        self._started = False

    def content(self, text: str) -> str:
        return self._frame(LlmDelta(**self._role(), content=text), None)

    def reply(self, answer: AgentReply) -> list[str]:
        if answer.end_call is not None:
            return [self._end_call(answer.end_call), self._frame(LlmDelta(), "tool_calls")]
        frames = [self.content(part) for part in answer.parts]
        if not self._started:
            frames.append(self._frame(LlmDelta(role="assistant"), None))
        return [*frames, self._frame(LlmDelta(), "stop")]

    def _end_call(self, end: EndCall) -> str:
        arguments = json.dumps({"reason": end.reason, "message": end.message}, ensure_ascii=False)
        call = LlmToolCall(
            index=0,
            id=f"call_{uuid.uuid4().hex}",
            type="function",
            function=LlmFunctionCall(name="end_call", arguments=arguments),
        )
        return self._frame(LlmDelta(**self._role(), tool_calls=[call]), None)

    def _role(self) -> dict[str, str]:
        if self._started:
            return {}
        self._started = True
        return {"role": "assistant"}

    def _frame(self, delta: LlmDelta, finish: FinishReason) -> str:
        choice = LlmChoice(index=0, delta=delta, finish_reason=finish)
        chunk = LlmChunk(
            id=self._id,
            object="chat.completion.chunk",
            created=self._created,
            model=VOICE_LLM_MODEL,
            choices=[choice],
        )
        return llm_frame(chunk)
