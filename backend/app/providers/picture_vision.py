from __future__ import annotations

from typing import Any

from app.providers import budget
from app.providers.base import ChatRequest, ProviderError
from app.providers.catalogue import AiTask
from app.providers.router import Principal
from app.research.image_screens import (
    NOT_SCREENED,
    VISION_ANSWER_SCHEMA,
    VISION_OUTPUT_TOKENS,
    ScreenTools,
    VisionRequest,
    VisionVerdict,
    unscreened,
    vision_prompt,
    vision_verdict,
)

from .vision_calls import (
    IMAGE_TOKENS,
    VisionAnswer,
    VisionAsk,
    VisionImage,
    VisionRoute,
    answered,
    reserved,
    vision_content,
    vision_routes,
)

__all__ = ["IMAGE_TOKENS", "VISION_TASK", "picture_screen_tools", "provider_content", "screen_with_vision"]

VISION_TASK = AiTask.CAPTION
NO_ROUTE = "No vision route is set up, so the picture was not looked at automatically."
NO_BUDGET = "The AI budget did not allow the screen."
FAILED = "The vision screen could not run ({kind})."
UNREAD = "The vision screen's answer could not be read."
SCREEN_DETAIL = "picture screen"


def picture_screen_tools() -> ScreenTools:
    return ScreenTools(vision=screen_with_vision)


def provider_content(kind: str, request: VisionRequest, text: str) -> list[dict[str, Any]]:
    return vision_content(kind, [VisionImage(mime=request.mime, data=request.preview), text])


async def screen_with_vision(request: VisionRequest) -> VisionVerdict:
    system, text = vision_prompt(ai_made=request.ai_made)
    route = await _cheapest(budget.estimate_tokens(f"{system}\n{text}") + IMAGE_TOKENS)
    if route is None:
        return unscreened(NO_ROUTE)
    ask = VisionAsk(
        task=VISION_TASK, use=SCREEN_DETAIL, principal=Principal(user_id=request.user_id, role=request.role)
    )
    event_id, allowed = await reserved(route, ask)
    if not allowed:
        return unscreened(NO_BUDGET)
    content: Any = provider_content(route.choice.kind, request, text)
    chat = ChatRequest(
        model=route.choice.model,
        system=system,
        user=content,
        max_tokens=VISION_OUTPUT_TOKENS,
        json_schema=dict(VISION_ANSWER_SCHEMA),
    )
    found = await answered(route, event_id, chat, SCREEN_DETAIL)
    if isinstance(found, ProviderError):
        return unscreened(FAILED.format(kind=found.kind or "error"))
    return _verdict(route, found, request)


async def _cheapest(prompt_tokens: int) -> VisionRoute | None:
    routes = await vision_routes(VISION_TASK, prompt_tokens=prompt_tokens, max_tokens=VISION_OUTPUT_TOKENS)
    return min(routes, key=lambda route: (route.estimate_usd, route.choice.ordinal), default=None)


def _verdict(route: VisionRoute, found: VisionAnswer, request: VisionRequest) -> VisionVerdict:
    result = found.result
    parsed = vision_verdict(result.text, ai_made=request.ai_made, faces=request.faces)
    flags, note = parsed if parsed is not None else ((NOT_SCREENED,), UNREAD)
    return VisionVerdict(
        ran=parsed is not None,
        flags=flags,
        note=note,
        provider=route.choice.provider,
        model=route.choice.model,
        usage_event_id=found.usage_event_id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=found.cost_usd,
    )
