from contextlib import asynccontextmanager
from typing import Any

import anthropic
import httpx2
import openai
import pytest
from google.genai import errors

from app.composer.prompt import compose_schema, regenerate_schema, section_schema
from app.composer.translation import translate_schema
from app.core.errors import NEXT_ROUTE_KINDS
from app.planner.drafting import plan_schema
from app.planner.understanding_prompt import understand_schema
from app.providers.anthropic_p import AnthropicAdapter
from app.providers.base import ChatRequest, ProviderError
from app.providers.gemini_p import GeminiAdapter
from app.providers.openai_p import OpenAICompatAdapter
from app.research.structured import schema_object, schema_problems

from .research.fixtures import AJRAKH

SONNET = "claude-sonnet-5-5"
FLASH = "gemini-3.8-flash"
GPT = "gpt-6-mini"
DEEPSEEK = "deepseek-chat"
NATIVE_FORMAT = {"type": "json_schema", "json_schema": {"name": "inference", "schema": None, "strict": False}}
STAGE = "77bf953a-03a3-54c3-a1bb-37ac338266df"


@pytest.mark.parametrize(
    "schema",
    [
        compose_schema(),
        section_schema(),
        section_schema([STAGE]),
        regenerate_schema(3),
        translate_schema(["s1.b1.1", "open.1"]),
        plan_schema(),
        understand_schema([AJRAKH]),
    ],
)
def test_every_schema_the_router_sends_keeps_to_the_portable_keywords(schema: dict[str, Any]) -> None:
    assert schema_problems(schema) == []


def test_the_schema_check_names_each_keyword_a_provider_refuses() -> None:
    schema = schema_object(
        text={"type": "string", "minLength": 1},
        items={"type": "array", "maxItems": 3, "items": {"type": "integer", "minimum": 0}},
    )
    assert schema_problems(schema) == [
        "$.text uses minLength",
        "$.items uses maxItems",
        "$.items[] uses minimum",
    ]


def test_the_schema_check_wants_closed_objects_that_require_every_property() -> None:
    loose = {"type": "object", "properties": {"a": {"type": "string"}}, "required": []}
    assert schema_problems(loose) == [
        "$ does not refuse additional properties",
        "$ does not require every property, in order",
    ]
    assert schema_problems({"type": "array"}) == ["$ is an array without one items schema"]
    assert schema_problems({"enum": ["a"]}) == ["$ has no single known type"]


def bad_request(message: str) -> anthropic.BadRequestError:
    response = httpx2.Response(400, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    return anthropic.BadRequestError(message, response=response, body=None)


class RefusingMessages:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.sent: list[dict[str, Any]] = []

    @asynccontextmanager
    async def stream(self, **params: Any):
        self.sent.append(params)
        raise self.error
        yield


def anthropic_adapter(error: Exception, learned: dict[str, list[str]] | None = None) -> tuple[Any, Any]:
    adapter = AnthropicAdapter(
        api_key="test-key", base_url=None, preset="anthropic", extra={}, learned=learned or {}
    )
    messages = RefusingMessages(error)
    adapter.client = type("Client", (), {"messages": messages})()
    return adapter, messages


async def test_a_refused_output_format_moves_to_the_next_route_and_never_drops_the_format() -> None:
    adapter, messages = anthropic_adapter(
        bad_request("output_config.format.schema: 'minLength' is not supported")
    )
    request = ChatRequest(model=SONNET, system="s", user="u", json_schema=compose_schema())
    with pytest.raises(ProviderError) as refused:
        await adapter.chat(request)
    assert (refused.value.kind, refused.value.status) == ("error", 400)
    assert refused.value.kind in NEXT_ROUTE_KINDS
    (sent,) = messages.sent
    assert sent["output_config"]["format"] == {"type": "json_schema", "schema": compose_schema()}
    assert adapter.learned == {}


async def test_a_format_learned_as_refused_before_is_still_sent() -> None:
    adapter, messages = anthropic_adapter(bad_request("json_schema is not supported"), {SONNET: ["format"]})
    with pytest.raises(ProviderError):
        await adapter.chat(ChatRequest(model=SONNET, system="s", user="u", json_schema=section_schema()))
    assert messages.sent[0]["output_config"]["format"]["schema"] == section_schema()


class RefusingModels:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.configs: list[Any] = []

    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any:
        self.configs.append(config)
        raise self.error


async def test_a_refused_gemini_schema_moves_to_the_next_route() -> None:
    adapter = GeminiAdapter(
        api_key="test-key", base_url=None, preset="gemini", extra={}, learned={FLASH: ["json_schema"]}
    )
    error = errors.ClientError(400, {"error": {"code": 400, "message": "response_json_schema is invalid"}})
    models = RefusingModels(error)
    adapter.client = type("Client", (), {"aio": type("Aio", (), {"models": models})()})()
    with pytest.raises(ProviderError) as refused:
        await adapter.chat(ChatRequest(model=FLASH, system="s", user="u", json_schema=plan_schema()))
    assert refused.value.kind in NEXT_ROUTE_KINDS
    (config,) = models.configs
    assert config.response_json_schema == plan_schema()
    assert adapter.learned == {FLASH: ["json_schema"]}


class RefusingCompletions:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.sent: list[dict[str, Any]] = []

    async def create(self, **params: Any) -> Any:
        self.sent.append(params)
        raise self.error


def openai_refusal(message: str) -> openai.BadRequestError:
    response = httpx2.Response(
        400, request=httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")
    )
    return openai.BadRequestError(message, response=response, body=None)


def openai_adapter(
    error: Exception, *, native: bool, model: str, learned: list[str]
) -> tuple[OpenAICompatAdapter, RefusingCompletions]:
    adapter = OpenAICompatAdapter(
        native=native,
        api_key="test-key",
        base_url=None,
        preset="openai" if native else "deepseek",
        extra={},
        learned={model: learned} if learned else {},
    )
    completions = RefusingCompletions(error)
    adapter.client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    return adapter, completions


@pytest.mark.parametrize(
    ("native", "model", "message", "sent_format"),
    [
        (
            True,
            GPT,
            "Invalid parameter: 'response_format' of type 'json_schema' is not supported",
            NATIVE_FORMAT,
        ),
        (False, DEEPSEEK, "This response_format type is unavailable now", {"type": "json_object"}),
        (False, DEEPSEEK, "json_object is not supported by this model", {"type": "json_object"}),
    ],
)
@pytest.mark.parametrize("learned", [[], ["json_schema", "response_format"]])
async def test_a_refused_openai_format_moves_to_the_next_route_and_is_never_dropped(
    native: bool, model: str, message: str, sent_format: dict[str, Any], learned: list[str]
) -> None:
    adapter, completions = openai_adapter(
        openai_refusal(message), native=native, model=model, learned=learned
    )
    request = ChatRequest(model=model, system="s", user="u", json_schema=section_schema())
    with pytest.raises(ProviderError) as refused:
        await adapter.chat(request)
    assert (refused.value.kind, refused.value.status) == ("error", 400)
    assert refused.value.kind in NEXT_ROUTE_KINDS
    (sent,) = completions.sent
    expected = sent_format
    if native:
        expected = {**sent_format, "json_schema": {**sent_format["json_schema"], "schema": section_schema()}}
    assert sent["response_format"] == expected
    assert adapter.learned == ({model: learned} if learned else {})


async def test_an_openai_refusal_of_another_parameter_is_still_adapted() -> None:
    adapter, completions = openai_adapter(
        openai_refusal("Unsupported parameter: 'temperature'"), native=True, model=GPT, learned=[]
    )
    request = ChatRequest(model=GPT, system="s", user="u", temperature=0.2, json_schema=plan_schema())
    with pytest.raises(ProviderError):
        await adapter.chat(request)
    first, second = completions.sent[:2]
    assert (first["temperature"], "temperature" in second) == (0.2, False)
    assert second["response_format"]["json_schema"]["schema"] == plan_schema()
    assert adapter.learned == {GPT: ["temperature"]}
