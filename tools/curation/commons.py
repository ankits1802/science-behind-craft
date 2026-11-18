from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlencode, urlsplit, urlunsplit

from app.sources.records import markup_text

from .polite import FetchFailed, PoliteHttp

__all__ = [
    "COMMONS_API",
    "COMMONS_FILE_PAGE",
    "CommonsPicture",
    "PictureFailed",
    "commons_picture",
    "imageinfo_url",
    "picture_lines",
]

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_FILE_PAGE = re.compile(r"^https://commons\.wikimedia\.org/wiki/(?P<title>File:[^?#]+)$")
EXTMETADATA = ("Artist", "LicenseShortName", "LicenseUrl")


class PictureFailed(Exception):
    pass


@dataclass(frozen=True)
class CommonsPicture:
    page_url: str
    url: str
    width: int
    height: int
    author: str | None
    licence: str | None
    licence_url: str | None


def imageinfo_url(page_url: str) -> str:
    found = COMMONS_FILE_PAGE.match(page_url)
    if found is None:
        raise PictureFailed(
            f"{page_url} is not a Wikimedia Commons file page (https://commons.wikimedia.org/wiki/File:...)"
        )
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiextmetadatafilter": "|".join(EXTMETADATA),
        "titles": unquote(found["title"]).replace("_", " "),
    }
    return f"{COMMONS_API}?{urlencode(params)}"


def commons_picture(http: PoliteHttp, page_url: str) -> CommonsPicture:
    try:
        answer = http.get(imageinfo_url(page_url))
    except FetchFailed as failure:
        raise PictureFailed(f"could not read {page_url}: {failure.reason}") from None
    info = _imageinfo(page_url, answer.body)
    width, height = info.get("width"), info.get("height")
    if not (isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0):
        raise PictureFailed(f"{page_url}: Commons gives no width and height for the file")
    metadata = info.get("extmetadata") or {}
    return CommonsPicture(
        page_url=page_url,
        url=_file_url(page_url, info.get("url")),
        width=width,
        height=height,
        author=_metadata(metadata, "Artist"),
        licence=_metadata(metadata, "LicenseShortName"),
        licence_url=_metadata(metadata, "LicenseUrl"),
    )


def picture_lines(picture: CommonsPicture) -> list[str]:
    return [
        f"pageUrl: {picture.page_url}",
        f"url: {picture.url}",
        f"width: {picture.width}",
        f"height: {picture.height}",
        f"author: {picture.author or ''}",
        f"licence: {picture.licence or ''}",
        f"licenceUrl: {picture.licence_url or ''}",
    ]


def _imageinfo(page_url: str, body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except UnicodeDecodeError, json.JSONDecodeError:
        raise PictureFailed(f"{page_url}: Commons answered with something other than JSON") from None
    pages = ((payload.get("query") or {}).get("pages") or []) if isinstance(payload, dict) else []
    page = pages[0] if pages and isinstance(pages[0], dict) else {}
    infos = page.get("imageinfo") or []
    if page.get("missing") or not infos or not isinstance(infos[0], dict):
        raise PictureFailed(f"{page_url}: Commons has no file by that name")
    return infos[0]


def _file_url(page_url: str, url: Any) -> str:
    if not isinstance(url, str) or not url.startswith("https://"):
        raise PictureFailed(f"{page_url}: Commons gives no https address for the file")
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _metadata(metadata: dict[str, Any], key: str) -> str | None:
    entry = metadata.get(key)
    return markup_text(entry.get("value")) if isinstance(entry, dict) else None
