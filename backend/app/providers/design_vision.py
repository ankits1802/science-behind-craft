from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.providers import budget
from app.providers.base import ChatRequest, ProviderError
from app.providers.router import Principal
from app.research.design_read import DESIGN_READ_CAP_USD, ModelReading, NotRead
from app.research.design_read_prompt import DesignPicture, DesignRequest

from .judge_routes import JUDGE_TASK
from .vision_calls import (
    IMAGE_TOKENS,
    VisionAsk,
    VisionImage,
    VisionPart,
    VisionRoute,
    answered,
    reserved,
    vision_content,
    vision_routes,
)

__all__ = [
    "DESIGN_EFFORT",
    "DESIGN_OUTPUT_TOKENS",
    "DESIGN_USE",
    "FAILED",
    "NO_BUDGET",
    "NO_ROUTE",
    "OVER_CAP",
    "best_route",
    "design_prompt_tokens",
    "read_design",
]

DESIGN_USE = "design read"
DESIGN_OUTPUT_TOKENS = 12_000
DESIGN_EFFORT = "medium"
NO_ROUTE = "No judge route reads pictures, so the designer's read did not run."
OVER_CAP = (
    "Reading these {pictures} pictures could cost up to ${estimate} on {model}, above the ${cap} one preview's "
    "read may spend, so it did not run."
)
NO_BUDGET = "The AI budget did not allow the designer's read."
FAILED = "The designer's read could not run ({kind})."


async def read_design(request: DesignRequest, principal: Principal) -> ModelReading | NotRead:
    routes = await vision_routes(
        JUDGE_TASK, prompt_tokens=design_prompt_tokens(request), max_tokens=DESIGN_OUTPUT_TOKENS
    )
    route = best_route(routes)
    if route is None:
        return NotRead(reason=NO_ROUTE)
    if route.estimate_usd > DESIGN_READ_CAP_USD:
        return NotRead(reason=_over_cap(route, request))
    ask = VisionAsk(
        task=JUDGE_TASK, use=DESIGN_USE, principal=principal, request_budget_usd=DESIGN_READ_CAP_USD
    )
    event_id, allowed = await reserved(route, ask)
    if not allowed:
        return NotRead(reason=NO_BUDGET)
    found = await answered(route, event_id, _chat(route, request), DESIGN_USE)
    if isinstance(found, ProviderError):
        return NotRead(reason=FAILED.format(kind=found.kind or "error"))
    return ModelReading(
        text=found.result.text,
        provider=route.choice.provider,
        model=route.choice.model,
        cost_usd=found.cost_usd,
    )


def best_route(routes: Sequence[VisionRoute]) -> VisionRoute | None:
    return min(routes, key=lambda route: route.choice.ordinal, default=None)


def design_prompt_tokens(request: DesignRequest) -> int:
    return budget.estimate_tokens(request.texts()) + IMAGE_TOKENS * request.pictures


def _chat(route: VisionRoute, request: DesignRequest) -> ChatRequest:
    content: Any = vision_content(route.choice.kind, [_part(part) for part in request.parts])
    return ChatRequest(
        model=route.choice.model,
        system=request.system,
        user=content,
        max_tokens=DESIGN_OUTPUT_TOKENS,
        reasoning=True,
        reasoning_effort=DESIGN_EFFORT,
        json_schema=dict(request.schema),
    )


def _part(part: str | DesignPicture) -> VisionPart:
    return VisionImage(mime=part.mime, data=part.data) if isinstance(part, DesignPicture) else part


def _over_cap(route: VisionRoute, request: DesignRequest) -> str:
    return OVER_CAP.format(
        pictures=request.pictures,
        estimate=route.estimate_usd,
        model=route.choice.model,
        cap=DESIGN_READ_CAP_USD,
    )
