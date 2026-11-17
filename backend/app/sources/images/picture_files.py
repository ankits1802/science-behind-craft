from __future__ import annotations

from urllib.parse import urlsplit

import httpx

from app.core.errors import ExternalFailure, InvalidInput

from ..http import RatePolicy, ResponseCache, SourceHttp

__all__ = ["PICTURE_HOSTS", "PICTURE_RATE", "PICTURE_TYPES", "PictureFiles", "picture_files"]

SERVICE = "picture_files"
PICTURE_HOSTS = frozenset({"upload.wikimedia.org", "api.openverse.org"})
PICTURE_TYPES = frozenset({"image/jpeg", "image/png", "image/gif", "image/webp"})
PICTURE_RATE = RatePolicy(min_interval=0.2)


class PictureFiles:
    def __init__(self, http: SourceHttp) -> None:
        self.http = http

    async def picture(self, url: str) -> bytes:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname not in PICTURE_HOSTS:
            raise InvalidInput(f"pictures are read only from {', '.join(sorted(PICTURE_HOSTS))}")
        response = await self.http.get(url)
        if response.content_type not in PICTURE_TYPES:
            raise ExternalFailure(
                f"{SERVICE} answered {response.content_type or 'no type'} for a picture", service=SERVICE
            )
        return response.body


def picture_files(client: httpx.AsyncClient) -> PictureFiles:
    return PictureFiles(
        SourceHttp(client=client, service=SERVICE, policy=PICTURE_RATE, cache=ResponseCache(max_entries=0))
    )
