import copy
import json
import re
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from app.api.router import api_router
from app.core.errors import InvalidInput
from app.schemas.voice import (
    MAX_SPOKEN_WORDS,
    AgentSessionStarted,
    ClientToolCall,
    RelaySessionStarted,
    VoiceAvailability,
    VoiceLanguageOption,
    VoiceSessionEnded,
    VoiceSessionRequest,
    VoiceSessionStarted,
    VoiceTranscript,
    VoiceTurnView,
    parse_relay_event,
    relay_frame,
)
from app.schemas.voice_llm import (
    DONE_FRAME,
    VOICE_LLM_PATH,
    LlmChatRequest,
    LlmChoice,
    LlmChunk,
    LlmDelta,
    LlmError,
    llm_error_frame,
    llm_frame,
)

from .golden import REPO, golden_json, golden_text, reproduces

CHUNK = "chatcmpl-bd260d5539e85cbf9e4d8dbe58ea75df"


@pytest.mark.parametrize(
    ("shape", "name"),
    [
        (VoiceAvailability, "voice.availability.golden.json"),
        (VoiceSessionStarted, "voice.session-agent.golden.json"),
        (VoiceSessionStarted, "voice.session-relay.golden.json"),
        (VoiceSessionEnded, "voice.session-ended.golden.json"),
        (VoiceTranscript, "voice.transcript.golden.json"),
    ],
)
def test_the_golden_voice_files_are_reproduced_byte_for_byte(shape: Any, name: str) -> None:
    assert reproduces(shape, name)


def test_the_session_answer_is_chosen_by_its_transport() -> None:
    adapter = TypeAdapter(VoiceSessionStarted)
    assert isinstance(
        adapter.validate_python(golden_json("voice.session-agent.golden.json")), AgentSessionStarted
    )
    relay = adapter.validate_python(golden_json("voice.session-relay.golden.json"))
    assert isinstance(relay, RelaySessionStarted) and relay.max_turn_seconds == 60
    with pytest.raises(ValidationError):
        adapter.validate_python({**golden_json("voice.session-relay.golden.json"), "conversationToken": "t"})


def chunk(delta: LlmDelta, finish: str | None) -> LlmChunk:
    return LlmChunk(
        id=CHUNK,
        object="chat.completion.chunk",
        created=1794825000,
        model="kalavigyan-voice",
        choices=[LlmChoice(index=0, delta=delta, finish_reason=finish)],
    )


def test_the_custom_llm_stream_is_produced_byte_for_byte() -> None:
    frames = [
        llm_frame(
            chunk(
                LlmDelta(role="assistant", content="Alum is used as a mordant to fasten the colours."), None
            )
        ),
        llm_frame(chunk(LlmDelta(content=" Source: GI Journal 188."), None)),
        llm_frame(chunk(LlmDelta(), "stop")),
        DONE_FRAME,
    ]
    assert "".join(frames) == golden_text("voice.llm.golden.sse")


def test_the_custom_llm_stream_ends_with_done_as_openai_streams_do() -> None:
    text = golden_text("voice.llm.golden.sse")
    assert text.endswith("data: [DONE]\n\n") and "\r" not in text
    for block in text.split("\n\n")[:-2]:
        payload = json.loads(block.removeprefix("data: "))
        assert LlmChunk.model_validate(payload).object == "chat.completion.chunk"


def test_the_inbound_request_ignores_the_client_extra_body() -> None:
    request = LlmChatRequest.model_validate(golden_json("voice.llm-request.golden.json"))
    assert request.messages[-1].content == "Why do Ajrakh printers use alum?"
    assert "elevenlabs_extra_body" not in request.model_dump()
    assert [tool["function"]["name"] for tool in request.tools] == ["end_call"]


def test_the_inbound_request_must_stream_a_user_turn() -> None:
    body = golden_json("voice.llm-request.golden.json")
    with pytest.raises(ValidationError, match="only as a stream"):
        LlmChatRequest.model_validate({**body, "stream": False})
    with pytest.raises(ValidationError, match="user message"):
        LlmChatRequest.model_validate({**body, "messages": body["messages"][:1]})


def test_an_error_is_one_openai_error_frame() -> None:
    error = LlmError.model_validate(
        {"error": {"message": "Not allowed.", "type": "invalid_request_error", "code": "unauthorized"}}
    )
    assert llm_error_frame(error) == (
        'data: {"error":{"message":"Not allowed.","type":"invalid_request_error","code":"unauthorized"}}\n\n'
    )


def test_tool_call_arguments_are_a_json_object() -> None:
    with pytest.raises(ValidationError, match="JSON object"):
        LlmDelta.model_validate(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "end_call", "arguments": "[]"},
                    }
                ]
            }
        )


def test_the_relay_turn_stream_is_produced_byte_for_byte() -> None:
    text = golden_text("voice.turn.golden.sse")
    frames = []
    for block in text.split("\n\n")[:-1]:
        name_line, data_line = block.split("\n")
        name, data = name_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: "))
        frames.append(relay_frame(name, parse_relay_event(name, data)))
    assert "".join(frames) == text
    assert [f.split("\n")[0] for f in frames] == [
        "event: heard",
        "event: status",
        "event: source",
        "event: sentence",
        "event: action",
        "event: spoken",
        "event: done",
    ]


def test_an_unknown_relay_event_or_tool_is_refused() -> None:
    with pytest.raises(InvalidInput, match="Unknown voice turn event"):
        relay_frame("transcript", {"text": "x"})
    with pytest.raises(ValidationError):
        TypeAdapter(ClientToolCall).validate_python(
            {"name": "open_url", "parameters": {"url": "https://x.test"}}
        )
    with pytest.raises(ValidationError):
        TypeAdapter(ClientToolCall).validate_python(
            {"name": "open_stage", "parameters": {"stageId": "not-a-uuid"}}
        )


def turn() -> dict[str, Any]:
    return copy.deepcopy(golden_json("voice.transcript.golden.json")["turns"][0])


def test_the_spoken_reply_says_each_cited_sentence_in_at_most_sixty_words() -> None:
    long = " ".join(["word"] * (MAX_SPOKEN_WORDS + 1))
    with pytest.raises(ValidationError, match="at most 60 words"):
        VoiceTurnView.model_validate({**turn(), "spoken": long})
    with pytest.raises(ValidationError, match="word for word"):
        VoiceTurnView.model_validate({**turn(), "spoken": "Alum fastens colours."})


def test_unconfigured_voice_offers_nothing() -> None:
    hidden = {
        "configured": False,
        "transport": None,
        "languages": [],
        "noticeVersion": None,
        "consentRequired": False,
        "remainingSeconds": 0,
    }
    assert not VoiceAvailability.model_validate(hidden).configured
    with pytest.raises(ValidationError, match="asks for nothing"):
        VoiceAvailability.model_validate({**hidden, "consentRequired": True})


def test_a_voice_language_is_an_answer_language_with_its_script_and_direction() -> None:
    for code in ("en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "or", "pa", "as", "ur"):
        assert VoiceSessionRequest.model_validate({"language": code}).language == code
    with pytest.raises(ValidationError):
        VoiceSessionRequest.model_validate({"language": "es"})
    urdu = {"code": "ur", "label": "Urdu", "autonym": "اردو", "script": "Arab", "direction": "rtl"}
    assert VoiceLanguageOption.model_validate(urdu).direction == "rtl"
    with pytest.raises(ValidationError):
        VoiceLanguageOption.model_validate({"code": "ur", "label": "Urdu"})
    golden = golden_json("voice.availability.golden.json")
    assert [(o["code"], o["direction"]) for o in golden["languages"]] == [
        ("en", "ltr"),
        ("hi", "ltr"),
        ("ta", "ltr"),
        ("ur", "rtl"),
    ]


def test_the_custom_llm_path_is_routed_from_cloudfront_to_the_api() -> None:
    assert VOICE_LLM_PATH.startswith(api_router.prefix + "/")
    cloudfront = (REPO / "infra" / "terraform" / "cloudfront.tf").read_text(encoding="utf-8")
    assert "default_cache_behavior" in cloudfront and "ordered_cache_behavior" not in cloudfront
    assert '"POST"' in cloudfront
    nginx = (REPO / "infra" / "terraform" / "user_data.sh").read_text(encoding="utf-8")
    assert re.search(r"location / \{\s+proxy_pass http://127\.0\.0\.1:8000;", nginx)
    assert "proxy_buffering off;" in nginx
