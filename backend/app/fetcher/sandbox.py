from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass

from app.core.errors import ExternalFailure
from app.research.fetcher import FETCH_MAX_REDIRECTS, FetchedPage, FetchRefused, FetchRequest
from app.sources.adapter import Clock, utc_now

from .extract import content_type_of, extract
from .robots import RobotsPolicy
from .targets import Target, checked_target, redirect_target
from .transport import Hop, PinnedHttp, remote_failure

__all__ = ["ACCEPT", "SandboxFetcher"]

ACCEPT = "text/html,application/xhtml+xml,application/pdf;q=0.9,text/plain;q=0.8"


@dataclass
class SandboxFetcher:
    http: PinnedHttp
    robots: RobotsPolicy
    clock: Clock = utc_now

    @classmethod
    def build(cls, http: PinnedHttp | None = None, *, clock: Clock = utc_now) -> SandboxFetcher:
        pinned = http or PinnedHttp()
        return cls(pinned, RobotsPolicy(pinned), clock)

    async def fetch(self, request: FetchRequest) -> FetchedPage:
        try:
            async with asyncio.timeout(request.timeout_seconds):
                return await self._fetch(request)
        except TimeoutError:
            raise FetchRefused(
                request.url, "TIME_LIMIT", f"not done in {request.timeout_seconds:g} seconds"
            ) from None

    async def _fetch(self, request: FetchRequest) -> FetchedPage:
        target = checked_target(request.url)
        redirects: list[str] = []
        hop = await self._hop(target, request)
        while hop.is_redirect:
            if len(redirects) == FETCH_MAX_REDIRECTS:
                raise FetchRefused(request.url, "TOO_MANY_REDIRECTS", f"more than {FETCH_MAX_REDIRECTS}")
            if not hop.location:
                raise ExternalFailure(f"{target.host} redirected without a location", service="fetcher")
            target = redirect_target(target, hop.location)
            redirects.append(target.url)
            hop = await self._hop(target, request)
        if not hop.is_success:
            raise remote_failure(hop)
        return await self._page(request, hop, redirects)

    async def _hop(self, target: Target, request: FetchRequest) -> Hop:
        await self.robots.check(target, timeout=request.timeout_seconds)
        return await self.http.get(
            target, max_bytes=request.max_bytes, timeout=request.timeout_seconds, accept=ACCEPT
        )

    async def _page(self, request: FetchRequest, hop: Hop, redirects: list[str]) -> FetchedPage:
        content_type = content_type_of(hop.target.url, hop.content_type)
        extracted = await asyncio.to_thread(extract, hop.target.url, content_type, hop.body, hop.charset)
        return FetchedPage(
            url=request.url,
            final_url=redirects[-1] if redirects else request.url,
            redirects=redirects,
            status=hop.status,
            content_type=content_type,
            bytes=len(hop.body),
            sha256=hashlib.sha256(hop.body).hexdigest(),
            fetched_at=self.clock(),
            text=extracted.text,
            truncated=extracted.truncated,
            metadata=extracted.metadata,
        )
