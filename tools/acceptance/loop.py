from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .costs import Budget, Prices, turn_cost

__all__ = [
    "API_FAILED",
    "CAP_REACHED",
    "CUT_OFF",
    "MODEL_STOPPED",
    "OFF_LIST",
    "PAUSED",
    "REFUSED",
    "TURNS_MAX",
    "TURN_LIMIT",
    "LoopOutcome",
    "Turn",
    "off_list_calls",
    "run_loop",
]

MODEL_STOPPED = "the model stopped"
CAP_REACHED = "the cap was reached"
REFUSED = "the model refused"
CUT_OFF = "the model was cut off"
OFF_LIST = "a tool outside the allowed list was called"
API_FAILED = "a request failed"
TURN_LIMIT = "the turn limit was reached"
PAUSED = "pause_turn"
TURNS_MAX = 150
ENDINGS = {
    "end_turn": MODEL_STOPPED,
    "stop_sequence": MODEL_STOPPED,
    "tool_use": MODEL_STOPPED,
    "refusal": REFUSED,
    "max_tokens": CUT_OFF,
    "model_context_window_exceeded": CUT_OFF,
}

Send = Callable[[list[dict[str, Any]]], Any]


@dataclass(frozen=True)
class Turn:
    number: int
    message: dict[str, Any]
    cost: Decimal


@dataclass
class LoopOutcome:
    stopped: str = ""
    detail: str = ""
    turns: list[Turn] = field(default_factory=list)


def off_list_calls(message: dict[str, Any], allowed: Iterable[str]) -> list[str]:
    permitted = set(allowed)
    return [
        block["name"]
        for block in message.get("content") or []
        if block.get("type") == "mcp_tool_use" and block.get("name") not in permitted
    ]


def run_loop(
    send: Send,
    opening: str,
    *,
    budget: Budget,
    prices: Prices,
    allowed: Iterable[str],
    failures: tuple[type[Exception], ...] = (),
    report: Callable[[Turn, Budget], None] | None = None,
) -> LoopOutcome:
    history: list[dict[str, Any]] = [{"role": "user", "content": opening}]
    outcome = LoopOutcome()
    while not outcome.stopped:
        if not budget.affords_next():
            return _ended(outcome, CAP_REACHED, f"spent {budget.spent} of {budget.cap}")
        if len(outcome.turns) >= TURNS_MAX:
            return _ended(outcome, TURN_LIMIT, f"{TURNS_MAX} turns")
        try:
            message = send(list(history))
        except failures as failed:
            return _ended(outcome, API_FAILED, f"{type(failed).__name__}: {failed}")
        turn = _charged(message, len(outcome.turns) + 1, budget, prices)
        outcome.turns.append(turn)
        history.append({"role": "assistant", "content": message.content})
        if report is not None:
            report(turn, budget)
        _judge(outcome, turn, allowed)
    return outcome


def _charged(message: Any, number: int, budget: Budget, prices: Prices) -> Turn:
    dumped = message.model_dump(mode="json")
    cost = turn_cost(dumped.get("usage") or {}, prices)
    budget.charge(cost)
    return Turn(number, dumped, cost)


def _judge(outcome: LoopOutcome, turn: Turn, allowed: Iterable[str]) -> None:
    strays = off_list_calls(turn.message, allowed)
    if strays:
        _ended(outcome, OFF_LIST, ", ".join(strays))
        return
    reason = turn.message.get("stop_reason")
    if reason == PAUSED:
        return
    _ended(outcome, ENDINGS.get(reason, MODEL_STOPPED), str(reason))


def _ended(outcome: LoopOutcome, stopped: str, detail: str) -> LoopOutcome:
    outcome.stopped = stopped
    outcome.detail = detail
    return outcome
