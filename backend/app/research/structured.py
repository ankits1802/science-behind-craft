from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from app.core.errors import ExternalFailure

from .base import ContractModel

__all__ = [
    "MODEL_SERVICE",
    "PORTABLE_SCHEMA_KEYWORDS",
    "StructuredModel",
    "StructuredReply",
    "reply_object",
    "schema_object",
    "schema_problems",
]

MODEL_SERVICE = "model"
CODE_FENCE = re.compile(r"^```[A-Za-z0-9_-]*\s*\n(?P<body>.*)\n\s*```$", re.DOTALL)
PORTABLE_SCHEMA_KEYWORDS = frozenset(
    {"type", "enum", "items", "properties", "required", "additionalProperties"}
)


class StructuredReply(ContractModel):
    text: str
    degraded: bool
    model: str | None = None


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


def schema_problems(schema: Mapping[str, Any], path: str = "$") -> list[str]:
    problems = [f"{path} uses {key}" for key in sorted(set(schema) - PORTABLE_SCHEMA_KEYWORDS)]
    kind = schema.get("type")
    if kind == "object":
        problems += _object_problems(schema, path)
    elif kind == "array":
        items = schema.get("items")
        if not isinstance(items, Mapping):
            problems.append(f"{path} is an array without one items schema")
        else:
            problems += schema_problems(items, f"{path}[]")
    elif kind not in ("string", "integer", "number", "boolean"):
        problems.append(f"{path} has no single known type")
    return problems


def _object_problems(schema: Mapping[str, Any], path: str) -> list[str]:
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        return [f"{path} is an object without properties"]
    problems = []
    if schema.get("additionalProperties") is not False:
        problems.append(f"{path} does not refuse additional properties")
    if list(schema.get("required", ())) != list(properties):
        problems.append(f"{path} does not require every property, in order")
    for name, child in properties.items():
        problems += schema_problems(child, f"{path}.{name}")
    return problems
