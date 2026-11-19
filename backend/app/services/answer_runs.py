from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .answering import AnswerAsk, AnswerPipeline, answer_question

__all__ = ["NOTHING_KEPT", "PROBLEM_EVENTS", "AnswerRun", "answer_to_the_end"]

PROBLEM_EVENTS = ("error", "not_enough_evidence")
DONE_EVENT = "done"
NOTHING_KEPT = (
    "This question was answered only from stored facts, so no answer was kept. Read the facts with get_facts, "
    "or ask on the site."
)


@dataclass(frozen=True)
class AnswerRun:
    answer_id: uuid.UUID | None
    problem: str | None


@dataclass
class _Collected:
    answer_id: uuid.UUID | None = None
    problems: list[str] = field(default_factory=list)

    async def emit(self, event: str, data: Any) -> None:
        if not isinstance(data, Mapping):
            return
        if event == DONE_EVENT and data.get("answerId"):
            self.answer_id = uuid.UUID(str(data["answerId"]))
        elif event in PROBLEM_EVENTS and data.get("message"):
            self.problems.append(str(data["message"]))

    def run(self) -> AnswerRun:
        if self.problems:
            return AnswerRun(answer_id=self.answer_id, problem=self.problems[-1])
        if self.answer_id is None:
            return AnswerRun(answer_id=None, problem=NOTHING_KEPT)
        return AnswerRun(answer_id=self.answer_id, problem=None)


async def answer_to_the_end(ask: AnswerAsk, pipeline: AnswerPipeline) -> AnswerRun:
    collected = _Collected()
    await answer_question(ask, pipeline, collected.emit)
    return collected.run()
