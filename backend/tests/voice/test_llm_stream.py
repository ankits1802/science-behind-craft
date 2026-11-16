import asyncio
import json
from typing import Any

import pytest

from app.schemas.voice_llm import LlmChunk, LlmError
from app.voice import llm
from app.voice.llm import AgentReply, EndCall, reply_stream

from ..contracts.golden import golden_text
from .fakes import ALUM, TURN_ID

CREATED = 1794825000


async def frames(reply: Any, language: str = "en") -> list[str]:
    return [frame async for frame in reply_stream(reply, turn_id=TURN_ID, created=CREATED, language=language)]


def payload(frame: str) -> dict[str, Any]:
    return json.loads(frame.removeprefix("data: "))


async def ready(reply: AgentReply) -> AgentReply:
    return reply


async def test_a_spoken_reply_streams_the_golden_custom_llm_frames() -> None:
    sent = await frames(ready(AgentReply(parts=(ALUM, " Source: GI Journal 188."))))
    assert "".join(sent) == golden_text("voice.llm.golden.sse")


async def test_a_slow_turn_streams_a_filler_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm, "FILLER_AFTER_SECONDS", 0.01)

    async def slow() -> AgentReply:
        await asyncio.sleep(0.1)
        return AgentReply(parts=(ALUM,))

    sent = await frames(slow())
    first, second = (LlmChunk.model_validate(payload(frame)) for frame in sent[:2])
    assert first.choices[0].delta.role == "assistant"
    assert first.choices[0].delta.content == "Let me check the sources... "
    assert second.choices[0].delta.role is None and second.choices[0].delta.content == ALUM
    assert sent[-1] == "data: [DONE]\n\n"


async def test_a_fast_turn_streams_no_filler() -> None:
    sent = await frames(ready(AgentReply(parts=(ALUM,))))
    assert payload(sent[0])["choices"][0]["delta"] == {"role": "assistant", "content": ALUM}


async def test_running_out_of_time_is_one_end_call_tool_call() -> None:
    end = EndCall(reason="quota", message="That is all the voice time for today.")
    sent = await frames(ready(AgentReply(end_call=end)))
    call, finish, done = sent
    delta = payload(call)["choices"][0]["delta"]
    assert delta["role"] == "assistant"
    [tool] = delta["tool_calls"]
    assert tool["function"]["name"] == "end_call"
    assert json.loads(tool["function"]["arguments"]) == {
        "reason": "quota",
        "message": "That is all the voice time for today.",
    }
    assert payload(finish)["choices"][0] == {"index": 0, "delta": {}, "finish_reason": "tool_calls"}
    assert done == "data: [DONE]\n\n"


async def test_a_failure_after_the_stream_started_is_one_error_frame() -> None:
    async def broken() -> AgentReply:
        raise RuntimeError("model down")

    error, done = await frames(broken())
    assert LlmError.model_validate(payload(error)).error.code == "unavailable"
    assert done == "data: [DONE]\n\n"


async def test_a_turn_with_nothing_to_say_still_closes_the_reply() -> None:
    opening, finish, _ = await frames(ready(AgentReply()))
    assert payload(opening)["choices"][0]["delta"] == {"role": "assistant"}
    assert payload(finish)["choices"][0]["finish_reason"] == "stop"
