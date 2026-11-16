import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

REPO = Path(__file__).resolve().parents[3]
SHARED = REPO / "shared"
PLAN = REPO / "docs" / "PLAN.md"


def golden_text(name: str) -> str:
    return (SHARED / name).read_text(encoding="utf-8")


def golden_json(name: str) -> Any:
    return json.loads(golden_text(name))


def dumped(shape: Any, value: Any) -> str:
    plain = TypeAdapter(shape).dump_python(value, mode="json", by_alias=True)
    return json.dumps(plain, indent=2, ensure_ascii=False) + "\n"


def reproduces(shape: Any, name: str) -> bool:
    text = golden_text(name)
    return dumped(shape, TypeAdapter(shape).validate_json(text)) == text


def plan_text() -> str:
    return PLAN.read_text(encoding="utf-8")
