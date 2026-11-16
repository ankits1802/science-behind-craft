from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from app.core.errors import ExternalFailure

from .base import ContractModel

__all__ = ["MODEL_SERVICE", "StructuredModel", "StructuredReply", "reply_object", "schema_object"]

MODEL_SERVICE = "model"
CODE_FENCE = re.compile(r"^```[A-Za-z0-9_-]*\s*\n(?P<body>.*)\n\s*```$", re.DOTALL)


class StructuredReply(ContractModel):
    text: str
    degraded: bool


@runtime_checkable
class StructuredModel(Protocol):
    async def __call__(self, *, system: str, user: str, schema: Mapping[str, Any]) -> StructuredReply: ...


def reply_object(reply: StructuredReply) -> dict[str, Any]:
    fenced = CODE_FENCE.match(reply.text)
    body = fenced.group("body") if fenced else reply.text
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as error:
        raise ExternalFailure(
            f"the model reply is not JSON (line {error.lineno}, column {error.colno})", service=MODEL_SERVICE
        ) from error
    if not isinstance(parsed, dict):
        raise ExternalFailure(
            f"the model reply is a JSON {type(parsed).__name__}, not an object", service=MODEL_SERVICE
        )
    return parsed


def schema_object(**properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }
