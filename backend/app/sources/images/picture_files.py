from __future__ import annotations

from urllib.parse import urlsplit

import httpx

from app.core.errors import ExternalFailure, InvalidInput

from ..http import RatePolicy, ResponseCache, SourceHttp

__all__ = ["PICTURE_HOSTS", "PICTURE_RATE", "PICTURE_TYPES", "PictureFiles", "picture_files", "site_host"]

SERVICE = "picture_files"
HTTPS = "https"
PICTURE_HOSTS = frozenset({"upload.wikimedia.org", "api.openverse.org"})
PICTURE_TYPES = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})
PICTURE_RATE = RatePolicy(min_interval=0.2)


class PictureFiles:
    def __init__(self, http: SourceHttp, hosts: frozenset[str] = PICTURE_HOSTS) -> None:
        self.http = http
        self.hosts = hosts

    async def picture(self, url: str) -> bytes:
        parts = urlsplit(url)
        if parts.scheme != HTTPS or parts.hostname not in self.hosts:
            raise InvalidInput(f"pictures are read only from {', '.join(sorted(self.hosts))}")
        response = await self.http.get(url)
        if response.content_type not in PICTURE_TYPES:
            raise ExternalFailure(
                f"{SERVICE} answered {response.content_type or 'no type'} for a picture", service=SERVICE
            )
        return response.body


def site_host(site: str | None) -> frozenset[str]:
    parts = urlsplit(site or "")
    return frozenset({parts.hostname}) if parts.scheme == HTTPS and parts.hostname else frozenset()


def picture_files(client: httpx.AsyncClient, *, site: str | None = None) -> PictureFiles:
    http = SourceHttp(client=client, service=SERVICE, policy=PICTURE_RATE, cache=ResponseCache(max_entries=0))
    return PictureFiles(http, PICTURE_HOSTS | site_host(site))
