from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.research.structured import StructuredModel, StructuredReply
from app.services.ai_providers import AiTask

from . import router
from .router import Principal, RouteTuning

__all__ = ["router_structured_model"]


def router_structured_model(
    task: AiTask, principal: Principal | None = None, *, tuning: RouteTuning | None = None
) -> StructuredModel:
    async def call(*, system: str, user: str, schema: Mapping[str, Any]) -> StructuredReply:
        result = await router.run(
            task, system=system, user=user, json_schema=dict(schema), principal=principal, tuning=tuning
        )
        return StructuredReply(text=result.text, degraded=result.degraded, model=result.model)

    return call
