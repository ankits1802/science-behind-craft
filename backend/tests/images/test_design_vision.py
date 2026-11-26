import uuid
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest

from app.providers import vision_calls
from app.providers.base import Adapter, ChatRequest, ChatResult, ProviderError
from app.providers.catalogue import AiTask
from app.providers.design_vision import (
    DESIGN_EFFORT,
    DESIGN_OUTPUT_TOKENS,
    FAILED,
    NO_ROUTE,
    read_design,
)
from app.providers.router import Principal, RouteChoice
from app.providers.spend_settings import MODEL_PRICES
from app.research.design_read import DESIGN_READ_CAP_USD, ModelReading, NotRead
from app.research.design_read_prompt import DesignPicture, DesignRequest, design_schema

from ..router_fakes import Recorded, anthropic_route, record_router

PRINCIPAL = Principal(user_id=uuid.UUID(int=3), role="RESEARCHER")
REQUEST = DesignRequest(
    system="You are a book designer.",
    parts=(
        "# The designer's critique",
        "Picture 1, chapter opening: the first screen",
        DesignPicture("opening", "the first screen", "image/jpeg", b"\xff\xd8one"),
        "Write the critique.",
    ),
    chapters=("opening",),
    schema=design_schema(["opening"]),
)
OPUS = anthropic_route("claude-opus-5-5")
ARGON = RouteChoice(
    ordinal=1,
    provider="GEMINI",
    provider_id=None,
    preset="gemini",
    kind="gemini",
    base_url=None,
    key_name="GEMINI_API_KEY",
    model="gemini-4-argon",
)


class Answering(Adapter):
    def __init__(self, requests: list[ChatRequest], failure: ProviderError | None = None) -> None:
        super().__init__(api_key="k", base_url=None, preset="anthropic", extra={}, learned={})
        self.requests = requests
        self.failure = failure

    async def chat(self, req: ChatRequest) -> ChatResult:
        self.requests.append(req)
        if self.failure is not None:
            raise self.failure
        return ChatResult(
            text='{"notes": [], "verdict": "Set well."}', input_tokens=9_000, output_tokens=2_000
        )

    async def list_models(self) -> list[dict]:
        return []


def reading(
    monkeypatch: pytest.MonkeyPatch,
    routes: list[RouteChoice],
    *,
    prices: dict[str, Any] | None = None,
    failure: ProviderError | None = None,
) -> Recorded:
    recorded = record_router(monkeypatch, settings={MODEL_PRICES: prices or {}})

    async def loaded(_session: Any, task: AiTask) -> list[RouteChoice]:
        assert task == AiTask.EVAL_JUDGE
        return routes

    async def settle(_session: Any, event_id: Any, **settled: Any) -> None:
        recorded.settled.append(settled)

    monkeypatch.setattr(vision_calls, "load_routes", loaded)
    monkeypatch.setattr(vision_calls, "build_adapter", lambda **_: Answering(recorded.requests, failure))
    monkeypatch.setattr(vision_calls, "sessionmaker", recorded.sessions)
    monkeypatch.setattr(vision_calls, "settle", settle)
    return recorded


async def test_the_read_goes_to_the_first_judge_route_whose_model_reads_pictures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded = reading(monkeypatch, [ARGON, replace(OPUS, ordinal=2)])
    found = await read_design(REQUEST, PRINCIPAL)
    assert isinstance(found, ModelReading)
    assert (found.provider, found.model, found.text) == (
        "ANTHROPIC",
        "claude-opus-5-5",
        '{"notes": [], "verdict": "Set well."}',
    )
    assert found.cost_usd == Decimal("0.076000")
    (sent,) = recorded.requests
    assert (sent.model, sent.max_tokens, sent.reasoning, sent.reasoning_effort) == (
        "claude-opus-5-5",
        DESIGN_OUTPUT_TOKENS,
        True,
        DESIGN_EFFORT,
    )
    assert sent.json_schema == REQUEST.schema and sent.system == REQUEST.system
    image = sent.user[2]
    assert image["type"] == "image" and image["source"]["media_type"] == "image/jpeg"
    assert [entry["outcome"] for entry in recorded.settled] == ["OK"]
    (reserved,) = recorded.reserved
    assert reserved.task == "EVAL_JUDGE" and Decimal(0) < reserved.estimatedCostUsd <= DESIGN_READ_CAP_USD


async def test_the_cost_cap_stops_the_read_before_anything_is_reserved_or_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded = reading(monkeypatch, [OPUS], prices={"claude-opus-5-5": {"in": 400, "out": 2000}})
    found = await read_design(REQUEST, PRINCIPAL)
    assert isinstance(found, NotRead) and f"above the ${DESIGN_READ_CAP_USD}" in found.reason
    assert recorded.requests == [] and recorded.reserved == [] and recorded.settled == []


async def test_without_a_judge_route_that_reads_pictures_nothing_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded = reading(monkeypatch, [ARGON])
    assert await read_design(REQUEST, PRINCIPAL) == NotRead(reason=NO_ROUTE)
    assert recorded.requests == [] and recorded.reserved == []


async def test_a_refused_read_is_settled_as_refused_and_says_it_did_not_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refusal = ProviderError("Claude declined the request (category: None)", kind="refusal")
    recorded = reading(monkeypatch, [OPUS], failure=refusal)
    assert await read_design(REQUEST, PRINCIPAL) == NotRead(reason=FAILED.format(kind="refusal"))
    assert [(entry["outcome"], entry["error_kind"]) for entry in recorded.settled] == [
        ("REFUSED_PROVIDER", "refusal")
    ]
