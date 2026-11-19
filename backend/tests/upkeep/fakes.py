from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime

from app.core.errors import ExternalFailure
from app.research.fetcher import FetchedPage, FetchRefused, FetchRequest

NIGHT = datetime(2026, 11, 20, 0, 30, tzinfo=UTC)
SNAPSHOT_STAMP = "20261120003000"


def fetched_page(url: str, text: str, *, truncated: bool = False) -> FetchedPage:
    body = text.encode("utf-8")
    return FetchedPage.model_validate(
        {
            "url": url,
            "finalUrl": url,
            "status": 200,
            "contentType": "text/html",
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "fetchedAt": NIGHT,
            "text": text,
            "truncated": truncated,
            "metadata": {},
        }
    )


def gone(url: str) -> ExternalFailure:
    return ExternalFailure(f"{url} answered 404", kind="not_found", status=404, service="fetcher")


def robots(url: str) -> FetchRefused:
    return FetchRefused(url, "ROBOTS_DISALLOWED")


class ScriptedFetcher:
    def __init__(self, outcomes: Mapping[str, FetchedPage | Exception]) -> None:
        self.outcomes = dict(outcomes)
        self.asked: list[str] = []

    async def fetch(self, request: FetchRequest) -> FetchedPage:
        url = str(request.url)
        self.asked.append(url)
        outcome = self.outcomes.get(url) or robots(url)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class ScriptedArchiver:
    def __init__(self, answers: Mapping[str, str | Exception] | None = None) -> None:
        self.answers = dict(answers or {})
        self.saved: list[str] = []

    async def save(self, url: str) -> str:
        self.saved.append(url)
        answer = self.answers.get(url, f"https://web.archive.org/web/{SNAPSHOT_STAMP}/{url}")
        if isinstance(answer, Exception):
            raise answer
        return answer


class CountingHook:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.triggered = 0

    async def trigger(self) -> None:
        self.triggered += 1
        if self.failure is not None:
            raise self.failure
