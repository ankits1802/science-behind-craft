import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from app.core.errors import InvalidInput
from app.providers.elevenlabs import ElevenLabs
from app.voice.agent import AGENT_NAME, LLM_SECRET_NAME, AgentPlan, agent_body, llm_base_url, provision_agent

PLAN = AgentPlan(
    api_base_url="https://d89rsltpszebp.cloudfront.net",
    llm_bearer="test-only-voice-llm-bearer-not-a-secret-0123456789",
    voice_id="JBFqnCBsd6RMkjVDRZzb",
    max_live_sessions=5,
)
TOOL_IDS = ["tool_map", "tool_stage", "tool_sources", "tool_image"]


def test_the_custom_llm_url_is_our_route_without_the_chat_suffix() -> None:
    assert llm_base_url("https://d89rsltpszebp.cloudfront.net/") == (
        "https://d89rsltpszebp.cloudfront.net/api/voice/llm/v1"
    )
    with pytest.raises(InvalidInput, match="https"):
        llm_base_url("http://d89rsltpszebp.cloudfront.net")


def test_the_agent_carries_plan_ten_four_settings() -> None:
    body = agent_body(PLAN, secret_id="secret_llm", tool_ids=TOOL_IDS)
    config = body["conversation_config"]
    assert config["turn"] == {
        "turn_timeout": 10,
        "turn_eagerness": "normal",
        "soft_timeout_config": {"timeout_seconds": 3.0},
    }
    assert config["conversation"]["max_duration_seconds"] == 600
    assert "interruption" in config["conversation"]["client_events"]
    assert config["agent"]["language"] == "en" and "en" not in config["language_presets"]
    assert config["language_presets"]["ur"] == {"overrides": {"tts": {"model_id": "eleven_v4_turbo"}}}
    assert len(config["language_presets"]) == 12
    prompt = config["agent"]["prompt"]
    assert sorted(prompt["built_in_tools"]) == ["end_call", "language_detection", "skip_turn"]
    assert prompt["built_in_tools"]["end_call"]["params"] == {"system_tool_type": "end_call"}
    assert prompt["tool_ids"] == TOOL_IDS
    assert prompt["custom_llm"]["api_key"] == {"secret_id": "secret_llm"}
    assert prompt["custom_llm"]["request_headers"] == {"X-KV-Conversation-Id": "{{system__conversation_id}}"}
    assert prompt["custom_llm"]["model_id"] == "kalavigyan-voice"


def test_the_agent_is_private_and_takes_no_client_overrides() -> None:
    settings = agent_body(PLAN, secret_id="secret_llm", tool_ids=TOOL_IDS)["platform_settings"]
    assert settings["auth"] == {"enable_auth": True}
    assert settings["overrides"]["custom_llm_extra_body"] is False
    flags = json.dumps(settings["overrides"]["conversation_config_override"])
    assert "true" not in flags
    assert settings["privacy"]["record_voice"] is False
    assert settings["call_limits"]["agent_concurrency_limit"] == 5
    assert PLAN.llm_bearer not in json.dumps(agent_body(PLAN, secret_id="secret_llm", tool_ids=TOOL_IDS))


class FakeElevenLabs:
    def __init__(
        self, *, agents: list[dict[str, Any]], tools: list[dict[str, Any]], secrets: list[dict[str, Any]]
    ):
        self.agents, self.tools, self.secrets = agents, tools, secrets
        self.calls: list[str] = []

    def handler(self) -> Callable[[httpx.Request], httpx.Response]:
        def answer(request: httpx.Request) -> httpx.Response:
            path, method = request.url.path, request.method
            self.calls.append(f"{method} {path}")
            if method == "GET":
                field = path.rsplit("/", 1)[-1]
                return httpx.Response(200, json={field: getattr(self, field), "has_more": False})
            if path == "/v1/convai/secrets":
                return httpx.Response(
                    200, json={"type": "stored", "secret_id": "secret_new", "name": LLM_SECRET_NAME}
                )
            if path == "/v1/convai/tools":
                name = json.loads(request.content)["tool_config"]["name"]
                return httpx.Response(200, json={"id": f"tool_{name}"})
            if path == "/v1/convai/agents/create":
                return httpx.Response(200, json={"agent_id": "agent_new"})
            return httpx.Response(200, json={})

        return answer

    def client(self) -> ElevenLabs:
        transport = httpx.MockTransport(self.handler())
        return ElevenLabs(api_key="test-only-elevenlabs-key", client=httpx.AsyncClient(transport=transport))


async def test_a_first_run_creates_the_secret_tools_and_agent() -> None:
    fake = FakeElevenLabs(agents=[], tools=[], secrets=[])
    done = await provision_agent(fake.client(), PLAN)
    assert (done.agent_id, done.created, done.secret_id) == ("agent_new", True, "secret_new")
    assert done.tool_ids == {
        name: f"tool_{name}" for name in ("show_on_map", "open_stage", "show_sources", "offer_image")
    }
    assert fake.calls.count("POST /v1/convai/tools") == 4 and "POST /v1/convai/agents/create" in fake.calls


async def test_a_second_run_updates_what_exists() -> None:
    fake = FakeElevenLabs(
        agents=[{"agent_id": "agent_test", "name": AGENT_NAME}],
        tools=[{"id": "tool_map", "tool_config": {"type": "client", "name": "show_on_map"}}],
        secrets=[{"type": "stored", "secret_id": "secret_llm", "name": LLM_SECRET_NAME}],
    )
    done = await provision_agent(fake.client(), PLAN)
    assert (done.agent_id, done.created, done.secret_id) == ("agent_test", False, "secret_llm")
    assert "PATCH /v1/convai/secrets/secret_llm" in fake.calls
    assert "PATCH /v1/convai/tools/tool_map" in fake.calls
    assert "PATCH /v1/convai/agents/agent_test" in fake.calls
    assert "POST /v1/convai/agents/create" not in fake.calls


async def test_two_agents_with_our_name_stop_the_run() -> None:
    twins = [{"agent_id": "a1", "name": AGENT_NAME}, {"agent_id": "a2", "name": AGENT_NAME}]
    fake = FakeElevenLabs(agents=twins, tools=[], secrets=[])
    with pytest.raises(InvalidInput, match="ELEVENLABS_AGENT_ID"):
        await provision_agent(fake.client(), PLAN)
