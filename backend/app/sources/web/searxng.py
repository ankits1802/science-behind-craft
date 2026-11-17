from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from app.core.errors import ExternalFailure
from app.research.evidence import EvidenceItem, SearchQuery
from app.research.fetcher import Fetcher
from app.research.images import (
    IMAGE_DESCRIPTION_MAX_CHARS,
    ImageCandidate,
    ImageQuery,
    clipped,
    same_site,
)

from ..adapter import Clock, checked_k, usable_records, utc_now
from ..http import RatePolicy, SourceHttp
from ..records import UnusableRecord, clean_text, https_or_none, title_of
from .page import WebPageAdapter

__all__ = ["SEARXNG_RATE", "SEARXNG_TIME_RANGES", "SearxngAdapter", "searxng_time_range"]

SEARXNG_RATE = RatePolicy(min_interval=0.2)
SEARXNG_TIME_RANGES = ((1, "day"), (7, "week"), (31, "month"), (366, "year"))
IMAGE_CATEGORY = "images"
RESOLUTION = re.compile(r"^\s*(\d{1,6})\s*[x×]\s*(\d{1,6})\s*$")
WWW = "www."


class SearxngAdapter(WebPageAdapter):
    name = "searxng"

    def __init__(self, http: SourceHttp, *, base_url: str, fetcher: Fetcher, clock: Clock = utc_now) -> None:
        super().__init__(http, fetcher=fetcher, clock=clock)
        self.endpoint = base_url.rstrip("/") + "/search"

    async def _search_records(self, query: SearchQuery, k: int) -> list[Any]:
        params = self._params(query.text, query.language)
        time_range = searxng_time_range(query.freshness_days)
        if time_range is not None:
            params["time_range"] = time_range
        return await self._results(params)

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

    async def images(self, query: ImageQuery, k: int) -> list[ImageCandidate]:
        wanted = checked_k(k)
        params = self._params(query.text, query.language) | {"categories": IMAGE_CATEGORY}
        results = await self._results(params)
        retrieved_at = self.clock()
        cards = usable_records(self.name, results, lambda record: self._link_card(record, retrieved_at))
        return cards[:wanted]

    def _link_card(self, record: Any, retrieved_at: datetime) -> ImageCandidate:
        if not isinstance(record, dict):
            raise UnusableRecord("not an object")
        page = https_or_none(record.get("url"))
        image = https_or_none(record.get("img_src"))
        if page is None or image is None:
            raise UnusableRecord("no https page or image")
        if not same_site(page, image):
            raise UnusableRecord("the image is not served by the page's own site")
        width, height = _resolution(record.get("resolution"))
        content = clean_text(record.get("content"))
        author = clean_text(record.get("author"))
        return ImageCandidate(
            provider=self.name,
            page_url=page,
            image_url=image,
            original_url=image,
            width=width,
            height=height,
            title=clipped(title_of(record.get("title"))),
            description=clipped(content, IMAGE_DESCRIPTION_MAX_CHARS) if content else None,
            author=clipped(author) if author else None,
            site=_site_name(page),
            retrieved_at=retrieved_at,
        )

    def _params(self, text: str, language: str) -> dict[str, str]:
        return {"q": text, "format": "json", "language": language, "safesearch": "1", "pageno": "1"}

    async def _results(self, params: dict[str, str]) -> list[Any]:
        response = await self.http.get(self.endpoint, params=params, headers={"Accept": "application/json"})
        payload = response.json(self.name)
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            raise ExternalFailure("searxng answered without a results list", service=self.name)
        return results


def searxng_time_range(freshness_days: int | None) -> str | None:
    if freshness_days is None:
        return None
    return next((name for days, name in SEARXNG_TIME_RANGES if freshness_days <= days), None)


def _resolution(value: Any) -> tuple[int | None, int | None]:
    found = RESOLUTION.match(value) if isinstance(value, str) else None
    if found is None or min(int(found.group(1)), int(found.group(2))) < 1:
        return None, None
    return int(found.group(1)), int(found.group(2))


def _site_name(page_url: str) -> str:
    host = (urlsplit(page_url).hostname or "").lower()
    return host.removeprefix(WWW) or page_url
