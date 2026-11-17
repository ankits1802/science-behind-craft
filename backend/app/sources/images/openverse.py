from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from app.core.errors import ExternalFailure
from app.research.images import (
    IMAGE_DESCRIPTION_MAX_CHARS,
    ImageCandidate,
    ImageQuery,
    clipped,
    openly_licensed,
)

from ..adapter import Clock, checked_k, usable_records, utc_now
from ..http import RatePolicy, SourceHttp
from ..records import UnusableRecord, clean_text, https_or_none, title_of

__all__ = [
    "OPENVERSE_ENDPOINT",
    "OPENVERSE_LICENCES",
    "OPENVERSE_PAGE_MAX",
    "OPENVERSE_RATE",
    "OpenverseAdapter",
]

OPENVERSE_ENDPOINT = "https://api.openverse.org/v1/images/"
OPENVERSE_RATE = RatePolicy(min_interval=1.0)
OPENVERSE_PAGE_MAX = 20
OPENVERSE_LICENCES = {"by": "CC BY", "by-sa": "CC BY-SA", "cc0": "CC0", "pdm": "Public Domain Mark"}
SOURCE_SITES = {"wikimedia": "Wikimedia Commons", "flickr": "Flickr"}
WWW = "www."


class OpenverseAdapter:
    name = "openverse"

    def __init__(self, http: SourceHttp, *, clock: Clock = utc_now) -> None:
        self.http = http
        self.clock = clock

    async def images(self, query: ImageQuery, k: int) -> list[ImageCandidate]:
        wanted = min(checked_k(k), OPENVERSE_PAGE_MAX)
        params = {
            "q": query.text,
            "license": ",".join(OPENVERSE_LICENCES),
            "page_size": str(wanted),
            "mature": "false",
        }
        response = await self.http.get(
            OPENVERSE_ENDPOINT, params=params, headers={"Accept": "application/json"}
        )
        results = _results(response.json(self.name))
        retrieved_at = self.clock()
        return usable_records(self.name, results, lambda record: self._candidate(record, retrieved_at))[
            :wanted
        ]

    def _candidate(self, record: Any, retrieved_at: datetime) -> ImageCandidate:
        if not isinstance(record, dict):
            raise UnusableRecord("not an object")
        if record.get("mature"):
            raise UnusableRecord("marked mature")
        licence = _licence(record)
        author = clean_text(record.get("creator"))
        if author is None:
            raise UnusableRecord("no creator to credit")
        page = https_or_none(record.get("foreign_landing_url"))
        shown = https_or_none(record.get("thumbnail"))
        original = https_or_none(record.get("url"))
        if page is None or shown is None or original is None:
            raise UnusableRecord("no https page or image")
        width, height = _size(record)
        candidate = ImageCandidate(
            provider=self.name,
            page_url=page,
            image_url=shown,
            original_url=original,
            width=width,
            height=height,
            title=clipped(title_of(record.get("title"))),
            description=_tags(record.get("tags")),
            author=clipped(author),
            site=_site(record.get("source"), page),
            licence=licence,
            licence_url=https_or_none(record.get("license_url")),
            retrieved_at=retrieved_at,
        )
        if not openly_licensed(candidate):
            raise UnusableRecord(f"licence {licence!r} is not on the open allow-list")
        return candidate


def _results(payload: Any) -> list[Any]:
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise ExternalFailure("openverse answered without a results list", service=OpenverseAdapter.name)
    return results


def _licence(record: dict[str, Any]) -> str:
    code = record.get("license")
    if code not in OPENVERSE_LICENCES:
        raise UnusableRecord(f"licence {code!r} is not open")
    version = clean_text(record.get("license_version"))
    name = OPENVERSE_LICENCES[code]
    return f"{name} {version}" if version else name


def _size(record: dict[str, Any]) -> tuple[int | None, int | None]:
    width, height = record.get("width"), record.get("height")
    if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
        return width, height
    return None, None


def _tags(tags: Any) -> str | None:
    names = (
        [clean_text(tag.get("name")) for tag in tags if isinstance(tag, dict)]
        if isinstance(tags, list)
        else []
    )
    text = ", ".join(name for name in names if name)
    return clipped(text, IMAGE_DESCRIPTION_MAX_CHARS) if text else None


def _site(source: Any, page_url: str) -> str:
    known = SOURCE_SITES.get(source) if isinstance(source, str) else None
    return known or (urlsplit(page_url).hostname or page_url).removeprefix(WWW)
