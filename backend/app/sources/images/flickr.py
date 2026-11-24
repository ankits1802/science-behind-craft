from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from app.core.errors import ExternalFailure, InvalidInput
from app.research.images import clipped
from app.research.open_pictures import FLICKR, OpenPictureRecord

from ..adapter import Clock, utc_now
from ..http import RatePolicy, SourceHttp
from ..records import clean_text, https_or_none, markup_text

__all__ = ["FLICKR_OEMBED", "FLICKR_RATE", "FlickrPhotos", "flickr_picture"]

FLICKR_OEMBED = "https://www.flickr.com/services/oembed/"
FLICKR_RATE = RatePolicy(min_interval=1.0)
PHOTO = "photo"
NOT_FOUND = "not_found"
NO_PHOTO = "Flickr shows no public photo at {url}"
NOT_A_PHOTO = "Flickr's record of {url} is not a photo with an https page and file"


class FlickrPhotos:
    name = "flickr"

    def __init__(self, http: SourceHttp, *, clock: Clock = utc_now) -> None:
        self.http = http
        self.clock = clock

    async def picture(self, page_url: str) -> OpenPictureRecord:
        params = {"url": page_url, "format": "json"}
        try:
            response = await self.http.get(
                FLICKR_OEMBED, params=params, headers={"Accept": "application/json"}
            )
        except ExternalFailure as failure:
            if failure.kind == NOT_FOUND:
                raise InvalidInput(NO_PHOTO.format(url=page_url)) from None
            raise
        record_url = f"{FLICKR_OEMBED}?{urlencode(params)}"
        return flickr_picture(
            response.json(self.name), asked=page_url, record_url=record_url, read_at=self.clock()
        )


def flickr_picture(payload: Any, *, asked: str, record_url: str, read_at: datetime) -> OpenPictureRecord:
    if not isinstance(payload, dict) or payload.get("type") != PHOTO:
        raise InvalidInput(NOT_A_PHOTO.format(url=asked))
    page = https_or_none(payload.get("web_page"))
    original = https_or_none(payload.get("url"))
    if page is None or original is None:
        raise InvalidInput(NOT_A_PHOTO.format(url=asked))
    width, height = _size(payload)
    return OpenPictureRecord(
        site=FLICKR,
        page_url=page,
        file_url=original,
        fetch_url=original,
        record_url=record_url,
        title=clipped(markup_text(payload.get("title")) or page),
        author=clean_text(payload.get("author_name")),
        licence=clean_text(payload.get("license")),
        licence_url=https_or_none(payload.get("license_url")),
        width=width,
        height=height,
        read_at=read_at,
    )


def _size(payload: dict[str, Any]) -> tuple[int | None, int | None]:
    width, height = _whole(payload.get("width")), _whole(payload.get("height"))
    return (width, height) if width and height else (None, None)


def _whole(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        return int(value) or None
    return None
