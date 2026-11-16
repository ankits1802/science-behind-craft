from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.errors import ExternalFailure
from app.research.evidence import EvidenceItem, SearchQuery
from app.research.fetcher import Fetcher

from ..adapter import Clock, utc_now
from ..http import RatePolicy, SourceHttp
from ..records import UnusableRecord
from .page import WebPageAdapter

__all__ = ["SEARXNG_RATE", "SEARXNG_TIME_RANGES", "SearxngAdapter"]

SEARXNG_RATE = RatePolicy(min_interval=0.2)
SEARXNG_TIME_RANGES = ((1, "day"), (7, "week"), (31, "month"), (366, "year"))


class SearxngAdapter(WebPageAdapter):
    name = "searxng"

    def __init__(self, http: SourceHttp, *, base_url: str, fetcher: Fetcher, clock: Clock = utc_now) -> None:
        super().__init__(http, fetcher=fetcher, clock=clock)
        self.endpoint = base_url.rstrip("/") + "/search"

    async def _search_records(self, query: SearchQuery, k: int) -> list[Any]:
        params = {
            "q": query.text,
            "format": "json",
            "language": query.language,
            "safesearch": "1",
            "pageno": "1",
        }
        time_range = searxng_time_range(query.freshness_days)
        if time_range is not None:
            params["time_range"] = time_range
        response = await self.http.get(self.endpoint, params=params, headers={"Accept": "application/json"})
        payload = response.json(self.name)
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            raise ExternalFailure("searxng answered without a results list", service=self.name)
        return results

    def _item(self, record: Any, retrieved_at: datetime) -> EvidenceItem:
        if not isinstance(record, dict):
            raise UnusableRecord("not an object")
        return self._hit(
            url=record.get("url"),
            title=record.get("title"),
            published=record.get("publishedDate"),
            publisher=None,
            retrieved_at=retrieved_at,
        )


def searxng_time_range(freshness_days: int | None) -> str | None:
    if freshness_days is None:
        return None
    return next((name for days, name in SEARXNG_TIME_RANGES if freshness_days <= days), None)
