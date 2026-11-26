from __future__ import annotations

import base64
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.core import managed_keys
from app.core.db import sessionmaker
from app.providers import budget, spend_settings
from app.providers.base import ChatRequest, ChatResult, ProviderError
from app.providers.catalogue import AiTask, model_for, supports
from app.providers.registry import build_adapter
from app.providers.router import (
    Principal,
    RouteChoice,
    estimate_for,
    load_routes,
    reserve,
    route_allowed,
    settle,
    settle_abandoned,
)

__all__ = [
    "CONTENT_KINDS",
    "IMAGE_TOKENS",
    "READS_PICTURES",
    "VisionAnswer",
    "VisionAsk",
    "VisionImage",
    "VisionPart",
    "VisionRoute",
    "answered",
    "reads_pictures",
    "reserved",
    "vision_content",
    "vision_routes",
]

READS_PICTURES = AiTask.CAPTION
IMAGE_TOKENS = 800
CONTENT_KINDS = frozenset({"anthropic", "gemini", "openai", "openai_compatible"})


@dataclass(frozen=True)
class VisionImage:
    mime: str
    data: bytes


VisionPart = str | VisionImage


@dataclass(frozen=True)
class VisionRoute:
    choice: RouteChoice
    estimate_usd: Decimal
    overrides: dict[str, Any]


@dataclass(frozen=True)
class VisionAsk:
    task: AiTask
    use: str
    principal: Principal
    request_budget_usd: Decimal | None = None


@dataclass(frozen=True)
class VisionAnswer:
    result: ChatResult
    cost_usd: Decimal
    usage_event_id: uuid.UUID


def vision_content(kind: str, parts: Sequence[VisionPart]) -> list[dict[str, Any]]:
    if kind == "gemini":
        return [{"role": "user", "parts": [_gemini_part(part) for part in parts]}]
    if kind == "anthropic":
        return [_anthropic_part(part) for part in parts]
    return [_openai_part(part) for part in parts]


def reads_pictures(choice: RouteChoice, task: AiTask) -> bool:
    return (
        route_allowed(choice, task)
        and choice.kind in CONTENT_KINDS
        and supports(choice.provider, choice.model, READS_PICTURES)
    )


async def vision_routes(task: AiTask, *, prompt_tokens: int, max_tokens: int) -> list[VisionRoute]:
    async with sessionmaker()() as session:
        routes = [route for route in await load_routes(session, task) if reads_pictures(route, task)]
        overrides = (await spend_settings.load_spend_settings(session)).get(spend_settings.MODEL_PRICES) or {}
        await managed_keys.refresh_if_stale(session)
    return [
        VisionRoute(
            choice=route,
            estimate_usd=estimate_for(
                route,
                task,
                prompt_tokens=prompt_tokens,
                max_tokens=max_tokens,
                units=None,
                overrides=overrides,
            ),
            overrides=overrides,
        )
        for route in routes
    ]


async def reserved(route: VisionRoute, ask: VisionAsk) -> tuple[uuid.UUID, bool]:
    async with sessionmaker()() as session:
        event_id, decision = await reserve(
            session,
            task=ask.task,
            choice=route.choice,
            principal=ask.principal,
            estimate_usd=route.estimate_usd,
            request_budget_usd=ask.request_budget_usd,
        )
    return event_id, decision.allowed


async def answered(
    route: VisionRoute, event_id: uuid.UUID, chat: ChatRequest, use: str
) -> VisionAnswer | ProviderError:
    try:
        result = await _called(route.choice, chat)
    except ProviderError as failure:
        await _settled_failure(event_id, failure, use)
        return failure
    except BaseException:
        await settle_abandoned(sessionmaker(), event_id, route.estimate_usd)
        raise
    cost = await _settled(route, event_id, result, use)
    return VisionAnswer(result=result, cost_usd=cost, usage_event_id=event_id)


def _gemini_part(part: VisionPart) -> dict[str, Any]:
    if isinstance(part, VisionImage):
        return {"inline_data": {"mime_type": part.mime, "data": part.data}}
    return {"text": part}


def _anthropic_part(part: VisionPart) -> dict[str, Any]:
    if isinstance(part, VisionImage):
        image = {"type": "base64", "media_type": part.mime, "data": _encoded(part)}
        return {"type": "image", "source": image}
    return {"type": "text", "text": part}


def _openai_part(part: VisionPart) -> dict[str, Any]:
    if isinstance(part, VisionImage):
        return {"type": "image_url", "image_url": {"url": f"data:{part.mime};base64,{_encoded(part)}"}}
    return {"type": "text", "text": part}


def _encoded(image: VisionImage) -> str:
    return base64.b64encode(image.data).decode("ascii")


async def _called(choice: RouteChoice, chat: ChatRequest) -> ChatResult:
    adapter = build_adapter(
        preset=choice.preset,
        kind=choice.kind,
        api_key=managed_keys.peek_secret(choice.key_name),
        api_key_name=choice.key_name,
        base_url=choice.base_url,
        extra=choice.extra,
        learned=choice.learned,
    )
    try:
        return await adapter.chat(chat)
    finally:
        await adapter.aclose()


async def _settled(route: VisionRoute, event_id: uuid.UUID, result: ChatResult, use: str) -> Decimal:
    choice = route.choice
    cost = budget.token_cost(
        model_for(choice.provider, choice.model),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cached_tokens=result.cached_input_tokens,
        overrides=route.overrides,
    )
    async with sessionmaker()() as session:
        await settle(
            session,
            event_id,
            outcome="OK",
            cost_usd=cost,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cached_tokens=result.cached_input_tokens,
            latency_ms=result.latency_ms,
            detail={"servedModel": result.meta.get("served_model"), "use": use},
        )
    return cost


async def _settled_failure(event_id: uuid.UUID, failure: ProviderError, use: str) -> None:
    async with sessionmaker()() as session:
        await settle(
            session,
            event_id,
            outcome="REFUSED_PROVIDER" if failure.kind == "refusal" else "ERROR",
            error_kind=failure.kind,
            detail={"status": failure.status, "use": use},
        )
