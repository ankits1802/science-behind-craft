from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

__all__ = [
    "ACCEPT",
    "INPUT_REQUIRED",
    "Answer",
    "Question",
    "answers_to",
    "choice",
    "input_required",
    "yes_no",
]

INPUT_REQUIRED = "input_required"
ELICIT = "elicitation/create"
ACCEPT, DECLINE, CANCEL = "accept", "decline", "cancel"
ACTIONS = frozenset({ACCEPT, DECLINE, CANCEL})


@dataclass(frozen=True)
class Question:
    key: str
    message: str
    properties: Mapping[str, Mapping[str, Any]]
    required: tuple[str, ...] = ()

    def request(self) -> dict[str, Any]:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {name: dict(value) for name, value in self.properties.items()},
        }
        if self.required:
            schema["required"] = list(self.required)
        return {
            "method": ELICIT,
            "params": {"mode": "form", "message": self.message, "requestedSchema": schema},
        }


@dataclass(frozen=True)
class Answer:
    action: str
    content: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    @property
    def accepted(self) -> bool:
        return self.action == ACCEPT

    def text(self, name: str) -> str | None:
        value = self.content.get(name) if self.accepted else None
        return (value.strip() or None) if isinstance(value, str) else None

    def says_yes(self, name: str) -> bool:
        return self.accepted and self.content.get(name) is True


def choice(title: str, description: str, options: Sequence[tuple[str, str]]) -> dict[str, Any]:
    return {
        "type": "string",
        "title": title,
        "description": description,
        "oneOf": [{"const": value, "title": label} for value, label in options],
    }


def yes_no(title: str, description: str) -> dict[str, Any]:
    return {"type": "boolean", "title": title, "description": description, "default": True}


def input_required(questions: Sequence[Question], state: str) -> dict[str, Any]:
    return {
        "resultType": INPUT_REQUIRED,
        "inputRequests": {question.key: question.request() for question in questions},
        "requestState": state,
    }


def answers_to(keys: Sequence[str], responses: Any) -> dict[str, Answer]:
    given = responses if isinstance(responses, Mapping) else {}
    found: dict[str, Answer] = {}
    for key in keys:
        response = given.get(key)
        if not isinstance(response, Mapping) or response.get("action") not in ACTIONS:
            continue
        content = response.get("content")
        held = MappingProxyType(dict(content)) if isinstance(content, Mapping) else MappingProxyType({})
        found[key] = Answer(action=str(response["action"]), content=held)
    return found
