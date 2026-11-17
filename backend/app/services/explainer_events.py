from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from app.research.explainer import Block
from app.research.sections import SectionSpec
from app.research.stream import Emit, StatusStep
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS

from .answer_events import OPEN_HEADING, OPEN_SECTION_ID
from .answer_trail import TrailLog

__all__ = ["ONCE_STEPS", "ExplainerStream", "shown_title", "status_message"]

ONCE_STEPS = frozenset(
    {"SEARCHING_STORED", "RESEARCHING", "READING", "COMPOSING", "WRITING_BACK", "TRANSLATING"}
)


def status_message(step: StatusStep, count: int = 0, craft: str = "", *, language: str = "") -> str:
    messages = {
        "RESOLVING": "Finding the craft",
        "PLANNING": f"Planning the research on {craft}" if craft else "Planning the research",
        "SEARCHING_STORED": "Searching stored findings",
        "RESEARCHING": f"Searching {_counted(count, 'live query', 'live queries')}",
        "READING": f"Reading the best of {_counted(count, 'source', 'sources')} found",
        "COMPOSING": f"Writing a cited answer from {_counted(count, 'passage', 'passages')}",
        "WRITING_BACK": f"Saving {_counted(count, 'source', 'sources')} for the next question",
        "TRANSLATING": f"Translating the answer into {language}",
    }
    return messages[step]


def shown_title(spec: SectionSpec, titles: Mapping[str, str]) -> dict[str, str]:
    title = titles.get(spec.id, spec.title)
    return {"title": title, "original": spec.title} if title != spec.title else {"title": title}


class ExplainerStream:
    def __init__(self, emit: Emit, *, language: str) -> None:
        self.emit = emit
        self.trail = TrailLog(emit)
        self.language = language
        self._lock = asyncio.Lock()
        self._sent_sources: set[str] = set()
        self._steps: set[str] = set()
        self._open_questions = 0

    async def status(self, step: StatusStep, count: int = 0, *, craft: str = "") -> None:
        if step in ONCE_STEPS and step in self._steps:
            return
        self._steps.add(step)
        label = ANSWER_LANGUAGE_SPECS[self.language].label
        await self.emit(
            "status", {"step": step, "message": status_message(step, count, craft, language=label)}
        )

    async def section_started(self, spec: SectionSpec, *, titles: Mapping[str, str], state: str) -> None:
        await self.emit(
            "section_started",
            {
                "id": spec.id,
                "discipline": spec.discipline,
                **shown_title(spec, titles),
                "order": spec.order,
                "state": state,
            },
        )

    async def section_state(self, section_id: str, state: str) -> None:
        await self.emit("section_state", {"sectionId": section_id, "state": state})

    async def section_done(self, section_id: str, *, searched: str | None) -> None:
        state = "EMPTY" if searched is not None else "READY"
        await self.emit("section_done", {"sectionId": section_id, "state": state, "searched": searched})

    async def blocks(
        self, section_id: str, blocks: Sequence[Block], sources: Mapping[str, Mapping[str, Any]]
    ) -> None:
        async with self._lock:
            for block in blocks:
                await self._sources(block.cited_source_ids(), sources)
                await self.emit("block", {"sectionId": section_id, "block": block})

    async def open_questions(
        self, sentences: Sequence[Mapping[str, Any]], sources: Mapping[str, Mapping[str, Any]]
    ) -> None:
        async with self._lock:
            for sentence in sentences:
                await self._sources(dict.fromkeys(c["sourceId"] for c in sentence["citations"]), sources)
                self._open_questions += 1
                numbered = {**sentence, "id": f"{OPEN_SECTION_ID}.{self._open_questions}"}
                await self.emit(
                    "open_question",
                    {"sectionId": OPEN_SECTION_ID, "heading": OPEN_HEADING, "sentence": numbered},
                )

    async def _sources(self, source_ids: Iterable[str], sources: Mapping[str, Mapping[str, Any]]) -> None:
        for source_id in source_ids:
            if source_id not in self._sent_sources:
                self._sent_sources.add(source_id)
                await self.emit("source", sources[source_id])


def _counted(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"
