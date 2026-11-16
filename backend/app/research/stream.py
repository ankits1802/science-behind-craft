from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from types import MappingProxyType
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, TypeAdapter, ValidationError, model_validator

from app.core.errors import InvalidInput
from app.models.knowledge import QUOTE_MAX_CHARS

from .base import ContractModel, HttpsUrl
from .crafts import MAX_CANDIDATES, CraftRef, CraftResolution
from .vocabulary import EvidenceLabel, ShownLevel, SourceType, TrustTier

__all__ = [
    "HEARTBEAT_FRAME",
    "HEARTBEAT_SECONDS",
    "STATUS_STEPS",
    "STREAM_EVENTS",
    "AnswerSentence",
    "Citation",
    "DoneEvent",
    "Emit",
    "ErrorEvent",
    "FollowUpsEvent",
    "MatchAmbiguous",
    "MatchNone",
    "MatchResolved",
    "NotEnoughEvidenceEvent",
    "OpenQuestionEvent",
    "ReactionEvent",
    "ResearchProgress",
    "SectionEvent",
    "SentenceEvent",
    "SourceRef",
    "StatusEvent",
    "StatusStep",
    "event_frame",
    "event_stream",
    "match_event",
    "parse_event",
    "sse_frame",
]

HEARTBEAT_SECONDS = 60
HEARTBEAT_FRAME = ": keep-alive\n\n"
STATUS_STEPS = (
    "RESOLVING",
    "PLANNING",
    "SEARCHING_STORED",
    "RESEARCHING",
    "READING",
    "COMPOSING",
    "WRITING_BACK",
    "TRANSLATING",
)

StatusStep = Literal[*STATUS_STEPS]
ResearchProgress = Callable[[StatusStep, int], Awaitable[None]]
Emit = Callable[[str, Any], Awaitable[None]]


def _absent(value: object) -> bool:
    return value is None


class SourceRef(ContractModel):
    id: str = Field(min_length=1)
    kind: SourceType
    title: str = Field(min_length=1)
    authors: list[str]
    year: int | None
    doi: str | None
    url: HttpsUrl | None
    publisher: str | None
    licence: str | None
    attribution: str | None
    reliability: TrustTier | None


class Citation(ContractModel):
    id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    quote: str | None = Field(max_length=QUOTE_MAX_CHARS)
    locator: str | None
    context: str | None
    evidence: EvidenceLabel
    level: ShownLevel


class AnswerSentence(ContractModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    level: ShownLevel
    citations: list[Citation] = Field(min_length=1)
    translated: bool = False
    original: str | None = Field(default=None, min_length=1, exclude_if=_absent)

    @model_validator(mode="after")
    def _translation_keeps_its_original(self) -> Self:
        if self.translated != (self.original is not None):
            raise ValueError("a translated sentence, and only a translated one, carries its original")
        return self


class MatchResolved(ContractModel):
    status: Literal["RESOLVED"]
    craft: CraftRef


class MatchAmbiguous(ContractModel):
    status: Literal["AMBIGUOUS"]
    candidates: list[CraftRef] = Field(min_length=1, max_length=MAX_CANDIDATES)


class MatchNone(ContractModel):
    status: Literal["NONE"]


class StatusEvent(ContractModel):
    step: StatusStep
    message: str = Field(min_length=1, max_length=300)


class SectionEvent(ContractModel):
    id: str = Field(min_length=1)
    heading: str = Field(min_length=1)
    original: str | None = Field(default=None, min_length=1, exclude_if=_absent)


class SentenceEvent(ContractModel):
    section_id: str = Field(min_length=1)
    sentence: AnswerSentence


class OpenQuestionEvent(ContractModel):
    section_id: str = Field(min_length=1)
    heading: str | None = None
    sentence: AnswerSentence


class ReactionEvent(ContractModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    equation: str = Field(min_length=1)
    balanced: bool
    level: ShownLevel
    conditions: str | None
    citations: list[Citation] = Field(min_length=1)


class FollowUpsEvent(ContractModel):
    items: list[str]


class DoneEvent(ContractModel):
    answer_id: str | None


class ErrorEvent(ContractModel):
    message: str = Field(min_length=1)


class NotEnoughEvidenceEvent(ContractModel):
    message: str = Field(min_length=1)


MatchEvent = Annotated[MatchResolved | MatchAmbiguous | MatchNone, Field(discriminator="status")]

STREAM_EVENTS: Mapping[str, TypeAdapter[Any]] = MappingProxyType(
    {
        "match": TypeAdapter(MatchEvent),
        "status": TypeAdapter(StatusEvent),
        "source": TypeAdapter(SourceRef),
        "section": TypeAdapter(SectionEvent),
        "sentence": TypeAdapter(SentenceEvent),
        "open_question": TypeAdapter(OpenQuestionEvent),
        "reaction": TypeAdapter(ReactionEvent),
        "follow_ups": TypeAdapter(FollowUpsEvent),
        "not_enough_evidence": TypeAdapter(NotEnoughEvidenceEvent),
        "done": TypeAdapter(DoneEvent),
        "error": TypeAdapter(ErrorEvent),
    }
)


def parse_event(name: str, data: Any) -> BaseModel:
    adapter = STREAM_EVENTS.get(name)
    if adapter is None:
        raise InvalidInput(f"Unknown answer stream event {name!r}")
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json", by_alias=True, exclude_unset=True)
    try:
        return adapter.validate_python(data)
    except ValidationError as exc:
        raise InvalidInput(f"The {name} event breaks the stream contract: {exc}") from exc


def event_frame(name: str, data: Any) -> str:
    payload = parse_event(name, data)
    return sse_frame(name, payload.model_dump(mode="json", by_alias=True, exclude_unset=True))


def sse_frame(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def match_event(resolution: CraftResolution) -> BaseModel:
    if resolution.status == "RESOLVED" and resolution.craft is not None:
        return MatchResolved(status="RESOLVED", craft=resolution.craft)
    if resolution.status == "AMBIGUOUS":
        return MatchAmbiguous(status="AMBIGUOUS", candidates=[c.craft for c in resolution.candidates])
    return MatchNone(status="NONE")


async def event_stream(
    produce: Callable[[Emit], Awaitable[None]], *, heartbeat_seconds: float = HEARTBEAT_SECONDS
) -> AsyncIterator[str]:
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def emit(name: str, data: Any) -> None:
        await queue.put(event_frame(name, data))

    async def run() -> None:
        try:
            await produce(emit)
        finally:
            await queue.put(None)

    task = asyncio.create_task(run())
    try:
        while True:
            try:
                frame = await asyncio.wait_for(queue.get(), heartbeat_seconds)
            except TimeoutError:
                yield HEARTBEAT_FRAME
                continue
            if frame is None:
                break
            yield frame
        await task
    finally:
        if not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
