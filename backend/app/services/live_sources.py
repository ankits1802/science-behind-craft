from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.errors import NotConfigured
from app.planner.reading import LiveSources
from app.services.scholarly_keys import scholarly_keys
from app.services.web_sources import web_search_config
from app.sources.fetcher_client import FetcherClient
from app.sources.http import source_client
from app.sources.reference.registry import reference_sources
from app.sources.scholarly.registry import scholarly_sources
from app.sources.web.registry import web_search

__all__ = ["DOI_SOURCE", "LIVE_SOURCES_TTL_SECONDS", "LiveSourcesStore", "live_source_client", "live_sources"]

DOI_SOURCE = "crossref"
LIVE_SOURCES_TTL_SECONDS = 600


def live_source_client() -> httpx.AsyncClient:
    return source_client(str(get_settings().research_contact_email))


async def live_sources(session: AsyncSession, client: httpx.AsyncClient) -> LiveSources:
    fetcher = FetcherClient(get_settings().fetcher_url, client)
    scholarly = scholarly_sources(await scholarly_keys(session), client)
    web = web_search(await web_search_config(session), client, fetcher)
    doi_source = next((adapter for adapter in scholarly.adapters if adapter.name == DOI_SOURCE), None)
    if doi_source is None:
        raise NotConfigured(DOI_SOURCE, f"The {DOI_SOURCE} adapter follows cited DOIs and must be built")
    return LiveSources(
        searchers=(*scholarly.adapters, *reference_sources(client), web),
        fetcher=fetcher,
        locator=scholarly.locator,
        doi_source=doi_source,
    )


class LiveSourcesStore:
    def __init__(
        self,
        *,
        ttl_seconds: float = LIVE_SOURCES_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        client_factory: Callable[[], httpx.AsyncClient] = live_source_client,
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._client_factory = client_factory
        self._client: httpx.AsyncClient | None = None
        self._sources: LiveSources | None = None
        self._built_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self, sessions: async_sessionmaker[AsyncSession]) -> LiveSources:
        async with self._lock:
            if self._sources is None or self._clock() - self._built_at >= self._ttl:
                if self._client is None:
                    self._client = self._client_factory()
                async with sessions() as session:
                    self._sources = await live_sources(session, self._client)
                self._built_at = self._clock()
            return self._sources

    async def aclose(self) -> None:
        client, self._client, self._sources = self._client, None, None
        if client is not None:
            await client.aclose()
