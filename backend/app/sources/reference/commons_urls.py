from __future__ import annotations

import re
from urllib.parse import unquote

__all__ = [
    "COMMONS_THUMB_NAME_MAX_BYTES",
    "COMMONS_WIDTHS",
    "commons_fitting_width",
    "commons_thumbnail_url",
    "standard_width",
]

COMMONS_UPLOADS = "https://upload.wikimedia.org/wikipedia/commons/"
COMMONS_WIDTHS = (330, 500, 960, 1280, 1920)
COMMONS_THUMB_NAME_MAX_BYTES = 120
ORIGINAL = re.compile(
    r"^https://upload\.wikimedia\.org/wikipedia/commons/(?P<a>[0-9a-f])/(?P<ab>[0-9a-f]{2})/(?P<name>[^/?#]+)$"
)
THUMB = re.compile(
    r"^https://upload\.wikimedia\.org/wikipedia/commons/thumb/(?P<a>[0-9a-f])/(?P<ab>[0-9a-f]{2})/"
    r"(?P<name>[^/?#]+)/\d+px-[^/?#]+$"
)
RASTER = re.compile(r"\.(jpe?g|png|gif|webp)$", re.IGNORECASE)
VECTOR = re.compile(r"\.svg$", re.IGNORECASE)


def commons_thumbnail_url(url: str, width: int) -> str | None:
    found = ORIGINAL.match(url) or THUMB.match(url)
    if found is None or width < 1:
        return None
    name = found["name"]
    if len(unquote(name).encode("utf-8")) > COMMONS_THUMB_NAME_MAX_BYTES:
        return None
    if VECTOR.search(name):
        suffix = ".png"
    elif RASTER.search(name):
        suffix = ""
    else:
        return None
    return f"{COMMONS_UPLOADS}thumb/{found['a']}/{found['ab']}/{name}/{width}px-{name}{suffix}"


def standard_width(requested: int) -> int:
    return next((width for width in COMMONS_WIDTHS if width >= requested), COMMONS_WIDTHS[-1])


def commons_fitting_width(requested: int, original: int) -> int | None:
    wanted = standard_width(requested)
    fitting = [width for width in COMMONS_WIDTHS if width <= original]
    if not fitting:
        return None
    return wanted if wanted <= original else fitting[-1]
