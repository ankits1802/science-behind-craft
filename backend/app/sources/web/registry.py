from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.research.fetcher import Fetcher

from ..adapter import Clock, utc_now
from ..http import ResponseCache, SourceHttp
from .brave import BRAVE_RATE, BraveAdapter
from .fallback import WebSearch
from .searxng import SEARXNG_RATE, SearxngAdapter

__all__ = ["WebSearchConfig", "web_search"]


@dataclass(frozen=True, repr=False)
class WebSearchConfig:
    searxng_url: str
    brave_api_key: str | None = None

    def __repr__(self) -> str:
        return f"WebSearchConfig(searxng_url={self.searxng_url!r}, brave={bool(self.brave_api_key)})"


def web_search(
    config: WebSearchConfig, client: httpx.AsyncClient, fetcher: Fetcher, *, clock: Clock = utc_now
) -> WebSearch:
    searxng = SearxngAdapter(
        SourceHttp(client=client, service="searxng", policy=SEARXNG_RATE, cache=ResponseCache()),
        base_url=config.searxng_url,
        fetcher=fetcher,
        clock=clock,
    )
    if not config.brave_api_key:
        return WebSearch(searxng)
    brave = BraveAdapter(
        SourceHttp(client=client, service="brave", policy=BRAVE_RATE, cache=ResponseCache()),
        api_key=config.brave_api_key,
        fetcher=fetcher,
        clock=clock,
    )
    return WebSearch(searxng, brave)
