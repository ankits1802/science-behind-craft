from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .costs import CACHE_READ_FACTOR, CACHE_WRITE_FACTOR, Prices, turn_cost
from .handed import HARNESS_USE
from .loop import LoopOutcome, Turn

__all__ = [
    "CHARS_PER_TOKEN",
    "Carried",
    "RunSpend",
    "ToolSpend",
    "carried_cost",
    "run_spend",
    "tokens_of",
]

CHARS_PER_TOKEN = Decimal("2.5")
MILLION = Decimal(1_000_000)
RESULT, USE = "mcp_tool_result", "mcp_tool_use"


@dataclass(frozen=True)
class Carried:
    name: str
    chars: int
    first_request: int
    written_by_model: bool = False
    is_error: bool = False
    is_result: bool = True


@dataclass(frozen=True)
class ToolSpend:
    name: str
    calls: int
    errors: int
    result_chars: int
    argument_chars: int
    tokens: int
    usd: Decimal


@dataclass(frozen=True)
class RunSpend:
    tools: list[ToolSpend]
    requests: int
    input_usd: Decimal
    output_usd: Decimal


def tokens_of(chars: int) -> int:
    return math.ceil(Decimal(chars) / CHARS_PER_TOKEN)


def carried_cost(item: Carried, requests: int, prices: Prices) -> Decimal:
    tokens = Decimal(tokens_of(item.chars))
    written = tokens * prices.output_per_mtok / MILLION if item.written_by_model else Decimal(0)
    if item.first_request >= requests:
        return written
    reads = requests - item.first_request - 1
    carried = tokens * prices.input_per_mtok * (CACHE_WRITE_FACTOR + CACHE_READ_FACTOR * reads) / MILLION
    return written + carried


def run_spend(outcome: LoopOutcome, prices: Prices) -> RunSpend:
    items, requests = _carried(outcome)
    output = sum(
        (Decimal(int((t.message.get("usage") or {}).get("output_tokens") or 0)) for t in outcome.turns),
        Decimal(0),
    )
    output_usd = output * prices.output_per_mtok / MILLION
    total = sum((turn_cost(t.message.get("usage") or {}, prices) for t in outcome.turns), Decimal(0))
    return RunSpend(_by_tool(items, requests, prices), requests, total - output_usd, output_usd)


def _carried(outcome: LoopOutcome) -> tuple[list[Carried], int]:
    items: list[Carried] = []
    names: dict[str, str] = {}
    request = 0
    for turn in outcome.turns:
        request = _turn_items(turn, (request, names), items)
        for call in (h for h in outcome.handed if h.turn == turn.number):
            items.append(Carried(call.name, call.chars, request, is_error=call.is_error))
    return items, request


def _turn_items(turn: Turn, at: tuple[int, dict[str, str]], items: list[Carried]) -> int:
    request, names = at
    blocks = turn.message.get("content") or []
    for index, block in enumerate(blocks):
        kind = block.get("type")
        if kind in (USE, HARNESS_USE):
            names[str(block.get("id"))] = str(block.get("name"))
            size = len(json.dumps(block.get("input") or {}, ensure_ascii=False))
            items.append(Carried(str(block.get("name")), size, request + 1, True, is_result=False))
        if kind == RESULT:
            name = names.get(str(block.get("tool_use_id")), "unknown")
            size = len("\n".join(str(i.get("text", "")) for i in _content(block) if i.get("type") == "text"))
            items.append(Carried(name, size, request + 1, is_error=bool(block.get("is_error"))))
            if index + 1 < len(blocks) and blocks[index + 1].get("type") != RESULT:
                request += 1
    return request + 1


def _content(block: dict[str, Any]) -> list[dict[str, Any]]:
    content = block.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return list(content or [])


def _by_tool(items: Sequence[Carried], requests: int, prices: Prices) -> list[ToolSpend]:
    grouped: dict[str, list[Carried]] = defaultdict(list)
    for item in items:
        grouped[item.name].append(item)
    rows = [
        ToolSpend(
            name=name,
            calls=sum(1 for item in found if not item.is_result),
            errors=sum(1 for item in found if item.is_result and item.is_error),
            result_chars=sum(item.chars for item in found if item.is_result),
            argument_chars=sum(item.chars for item in found if not item.is_result),
            tokens=sum(tokens_of(item.chars) for item in found),
            usd=sum((carried_cost(item, requests, prices) for item in found), Decimal(0)),
        )
        for name, found in grouped.items()
    ]
    return sorted(rows, key=lambda row: (-row.usd, row.name))
