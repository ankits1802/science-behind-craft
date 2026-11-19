import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from app.research.candidate_gates import HeldFact
from app.research.fetcher import FetchedPage, FetchRequest, PageMetadata
from app.research.structured import StructuredReply

FETCHED_AT = datetime(2026, 11, 19, 9, 30, tzinfo=UTC)
PAGE_URL = "https://crafts.example.org/ajrakh/indigo"
PAGE_TEXT = (
    "Ajrakh printers of Dhamadka resist the cloth with a paste of lime and gum arabic before the indigo vat. "
    "The cloth is dipped in the vat four times, and the colour deepens with every dip as air oxidises the dye."
)
QUOTE = "The cloth is dipped in the vat four times"
SECOND_QUOTE = "the colour deepens with every dip as air oxidises the dye"
STATEMENT = "Ajrakh cloth is dipped in the indigo vat four times, the colour deepening with each dip."
JUDGE_MODEL = "judge-model-1"


def fact_id(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"test-knowledge-writes/{name}")


def page(
    text: str = PAGE_TEXT, *, licence: str | None = None, title: str | None = "Indigo in Ajrakh"
) -> FetchedPage:
    return FetchedPage(
        url=PAGE_URL,
        final_url=PAGE_URL,
        status=200,
        content_type="text/html",
        bytes=len(text),
        sha256="0" * 64,
        fetched_at=FETCHED_AT,
        text=text,
        truncated=False,
        metadata=PageMetadata(title=title, licence=licence),
    )


class FakeFetcher:
    def __init__(self, pages: Mapping[str, FetchedPage | Exception]) -> None:
        self.pages = dict(pages)
        self.asked: list[str] = []

    async def fetch(self, request: FetchRequest) -> FetchedPage:
        self.asked.append(request.url)
        found = self.pages[request.url]
        if isinstance(found, Exception):
            raise found
        return found


class FakeEmbedder:
    def __init__(self, vector: Sequence[float]) -> None:
        self.vector = list(vector)
        self.calls: list[list[str]] = []

    async def __call__(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [list(self.vector) for _ in texts]


class FakeJudge:
    def __init__(self, *replies: Mapping[str, Any]) -> None:
        self.replies = [dict(reply) for reply in replies]
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, *, system: str, user: str, schema: Mapping[str, Any]) -> StructuredReply:
        self.calls.append({"system": system, "user": user, "schema": dict(schema)})
        reply = self.replies.pop(0)
        return StructuredReply(text=json.dumps(reply), degraded=False, model=JUDGE_MODEL)


class FakeHeldFacts:
    def __init__(self, nearest: Sequence[HeldFact] = (), twins: Sequence[HeldFact] = ()) -> None:
        self.held_nearest = list(nearest)
        self.held_twins = list(twins)
        self.asked: list[tuple[str, Any]] = []

    async def nearest(self, field: str | None, vector: Sequence[float], limit: int) -> list[HeldFact]:
        self.asked.append(("nearest", (field, limit)))
        return self.held_nearest[:limit]

    async def twins(self, field: str | None, statement: str) -> list[HeldFact]:
        self.asked.append(("twins", (field, statement)))
        return list(self.held_twins)


def held(name: str, text: str, similarity: float) -> HeldFact:
    return HeldFact(id=fact_id(name), text=text, similarity=similarity)
