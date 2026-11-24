from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal
from urllib.parse import SplitResult, parse_qs, quote, unquote, urlsplit

from pydantic import AwareDatetime, Field

from app.core.errors import InvalidInput
from app.models.enums import OPEN_PICTURE_SITES
from app.models.open_pictures import (
    OPEN_AUTHOR_CHARS,
    OPEN_CREDIT_CHARS,
    OPEN_LICENCE_CHARS,
    OPEN_TITLE_CHARS,
)

from .base import ContractModel, HttpsUrl
from .images import clipped
from .licences import ALL_RIGHTS_RESERVED, NO_DERIVATIVES, NON_COMMERCIAL, licence_restriction, open_licence

__all__ = [
    "COMMONS",
    "FLICKR",
    "OPENVERSE",
    "OPEN_TERMS_VERSION",
    "PHOTO_PREFIX",
    "SITE_NAMES",
    "OpenLink",
    "OpenPictureRecord",
    "OpenSource",
    "credited_author",
    "credited_licence",
    "credited_via",
    "flickr_photo_id",
    "open_link",
    "open_source",
    "photo_credit",
]

COMMONS, OPENVERSE, FLICKR = OPEN_PICTURE_SITES
SITE_NAMES = {COMMONS: "Wikimedia Commons", OPENVERSE: "Openverse", FLICKR: "Flickr"}
OPEN_TERMS_VERSION = "open-licence-2026-11-24"
PHOTO_PREFIX = "Photo: "
ACCEPTED = "KalaVigyan takes only public domain, CC0, CC BY or CC BY-SA pictures, any version"
NOT_A_PICTURE_PAGE = (
    "{url} is not a picture's page on Wikimedia Commons (commons.wikimedia.org/wiki/File:...), Openverse "
    "(openverse.org/image/<id>) or Flickr (flickr.com/photos/<owner>/<id>)"
)
NO_LICENCE = f"Its page states no licence, so it cannot be shown; {ACCEPTED}."
RESTRICTED = "Its licence, {licence}, {why}; " + ACCEPTED + "."
NOT_OPEN = "Its licence, {licence}, is not one KalaVigyan takes; " + ACCEPTED + "."
NO_AUTHOR = "Its page names no author to credit, so it cannot be shown."
WHY_RESTRICTED = {
    NON_COMMERCIAL: "forbids commercial use (NC)",
    NO_DERIVATIVES: "forbids changes such as a crop (ND)",
    ALL_RIGHTS_RESERVED: "reserves all rights",
}
UNCREDITED = frozenset(
    {"unknown", "unknown author", "author unknown", "anonymous", "not provided", "n/a", "none", "no author"}
)
HIDDEN_CATEGORIES = frozenset({"Cc", "Cf"})
COMMONS_HOSTS = frozenset({"commons.wikimedia.org", "commons.m.wikimedia.org"})
UPLOAD_HOST = "upload.wikimedia.org"
COMMONS_WIKI = "https://commons.wikimedia.org/wiki/"
WIKI_PATH = "/wiki/"
INDEX_PATH = "/w/index.php"
FILE_PREFIX = "File:"
FILE_TITLE = re.compile(r"^(?:File|Image):(?P<name>[^/#?]+\.[A-Za-z0-9]{2,5})$", re.IGNORECASE)
COMMONS_UPLOAD = re.compile(r"^/wikipedia/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/(?P<name>[^/]+)")
IDENTIFIER = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
OPENVERSE_HOSTS = frozenset({"openverse.org", "www.openverse.org"})
OPENVERSE_API_HOST = "api.openverse.org"
OPENVERSE_PAGE = re.compile(rf"^/(?:[a-z]{{2,3}}(?:-[A-Za-z]{{2,4}})?/)?image/(?P<id>{IDENTIFIER})/?$")
OPENVERSE_RECORD = re.compile(rf"^/v1/images/(?P<id>{IDENTIFIER})/?$")
FLICKR_HOSTS = frozenset({"www.flickr.com", "flickr.com", "m.flickr.com"})
FLICKR_SHORT_HOST = "flic.kr"
FLICKR_PHOTO = re.compile(r"^/photos/(?P<owner>[A-Za-z0-9@_.-]+)/(?P<id>\d{1,20})(?:/.*)?$")
FLICKR_SHORT = re.compile(r"^/p/(?P<code>[1-9a-km-zA-HJ-NP-Z]{1,16})/?$")
BASE58 = "123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
CC_URL = re.compile(
    r"creativecommons\.org/(?:licenses/(?P<kind>by|by-sa)/(?P<version>\d+(?:\.\d+)?)"
    r"|publicdomain/(?P<dedication>zero|mark)/(?P<dedicated>\d+(?:\.\d+)?))",
    re.IGNORECASE,
)
DEDICATIONS = {"zero": "CC0", "mark": "Public Domain Mark"}

OpenSite = Literal[*OPEN_PICTURE_SITES]


@dataclass(frozen=True)
class OpenLink:
    site: str
    key: str
    url: str


class OpenPictureRecord(ContractModel):
    site: OpenSite
    page_url: HttpsUrl
    file_url: HttpsUrl
    fetch_url: HttpsUrl
    record_url: HttpsUrl
    title: str = Field(min_length=1, max_length=OPEN_TITLE_CHARS)
    author: str | None = None
    licence: str | None = Field(default=None, max_length=OPEN_LICENCE_CHARS)
    licence_url: HttpsUrl | None = None
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    original_site: str | None = Field(default=None, max_length=OPEN_TITLE_CHARS)
    read_at: AwareDatetime


class OpenSource(ContractModel):
    site: OpenSite
    page_url: HttpsUrl
    file_url: HttpsUrl
    record_url: HttpsUrl
    title: str = Field(min_length=1, max_length=OPEN_TITLE_CHARS)
    author: str = Field(min_length=1, max_length=OPEN_AUTHOR_CHARS)
    licence: str = Field(min_length=1, max_length=OPEN_LICENCE_CHARS)
    licence_url: HttpsUrl | None
    credit: str = Field(min_length=1, max_length=OPEN_CREDIT_CHARS)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    read_at: AwareDatetime


def open_link(url: str) -> OpenLink:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if parts.scheme == "https":
        for read in (_commons_link, _openverse_link, _flickr_link):
            found = read(host, parts)
            if found is not None:
                return found
    raise InvalidInput(NOT_A_PICTURE_PAGE.format(url=url))


def open_source(record: OpenPictureRecord) -> OpenSource:
    licence = credited_licence(record.licence, record.licence_url)
    author = credited_author(record.author)
    via = credited_via(record.site, record.original_site)
    return OpenSource(
        site=record.site,
        page_url=record.page_url,
        file_url=record.file_url,
        record_url=record.record_url,
        title=clipped(record.title, OPEN_TITLE_CHARS),
        author=author,
        licence=licence,
        licence_url=record.licence_url,
        credit=clipped(photo_credit(author, licence, via), OPEN_CREDIT_CHARS),
        width=record.width,
        height=record.height,
        read_at=record.read_at,
    )


def credited_licence(name: str | None, url: str | None) -> str:
    stated = _visible(name) or None
    if stated is None and not url:
        raise InvalidInput(NO_LICENCE)
    named = stated or str(url)
    restriction = licence_restriction(stated) or licence_restriction(url)
    if restriction is not None:
        raise InvalidInput(RESTRICTED.format(licence=named, why=WHY_RESTRICTED[restriction]))
    if not (open_licence(stated) or open_licence(url)):
        raise InvalidInput(NOT_OPEN.format(licence=named))
    if stated is not None and open_licence(stated):
        return clipped(stated, OPEN_LICENCE_CHARS)
    return _licence_of_url(url) or named


def credited_author(author: str | None) -> str:
    shown = _visible(author)
    if not shown or shown.casefold().rstrip(".") in UNCREDITED:
        raise InvalidInput(NO_AUTHOR)
    return clipped(shown, OPEN_AUTHOR_CHARS)


def credited_via(site: str, original_site: str | None) -> str:
    if site == OPENVERSE and original_site:
        return f"{SITE_NAMES[OPENVERSE]} from {original_site}"
    return SITE_NAMES[site]


def photo_credit(author: str | None, licence: str | None, site: str) -> str:
    named = ", ".join(part for part in (author, licence) if part)
    return f"{PHOTO_PREFIX}{named}, via {site}" if named else f"{PHOTO_PREFIX}{site}"


def flickr_photo_id(code: str) -> int:
    number = 0
    for char in code:
        number = number * len(BASE58) + BASE58.index(char)
    return number


def _commons_link(host: str, parts: SplitResult) -> OpenLink | None:
    if host == UPLOAD_HOST:
        uploaded = COMMONS_UPLOAD.match(parts.path)
        return None if uploaded is None else _commons_file(unquote(uploaded["name"]))
    if host not in COMMONS_HOSTS:
        return None
    if parts.path.startswith(WIKI_PATH):
        title = unquote(parts.path.removeprefix(WIKI_PATH))
    elif parts.path == INDEX_PATH:
        title = (parse_qs(parts.query).get("title") or [""])[0]
    else:
        return None
    found = FILE_TITLE.match(title)
    return None if found is None else _commons_file(found["name"])


def _commons_file(name: str) -> OpenLink:
    key = f"{FILE_PREFIX}{name.replace('_', ' ').strip()}"
    return OpenLink(COMMONS, key, f"{COMMONS_WIKI}{quote(key.replace(' ', '_'), safe=':(),')}")


def _openverse_link(host: str, parts: SplitResult) -> OpenLink | None:
    if host in OPENVERSE_HOSTS:
        found = OPENVERSE_PAGE.match(parts.path)
    elif host == OPENVERSE_API_HOST:
        found = OPENVERSE_RECORD.match(parts.path)
    else:
        return None
    if found is None:
        return None
    key = found["id"].lower()
    return OpenLink(OPENVERSE, key, f"https://openverse.org/image/{key}")


def _flickr_link(host: str, parts: SplitResult) -> OpenLink | None:
    if host in FLICKR_HOSTS:
        photo = FLICKR_PHOTO.match(parts.path)
        if photo is None:
            return None
        return OpenLink(FLICKR, photo["id"], f"https://www.flickr.com/photos/{photo['owner']}/{photo['id']}/")
    if host == FLICKR_SHORT_HOST:
        short = FLICKR_SHORT.match(parts.path)
        if short is None:
            return None
        return OpenLink(FLICKR, str(flickr_photo_id(short["code"])), f"https://flic.kr/p/{short['code']}")
    return None


def _licence_of_url(url: str | None) -> str | None:
    found = CC_URL.search(url or "")
    if found is None:
        return None
    if found["kind"] is not None:
        return f"CC {found['kind'].upper()} {found['version']}"
    return f"{DEDICATIONS[found['dedication'].lower()]} {found['dedicated']}"


def _visible(text: str | None) -> str:
    kept = "".join(char for char in text or "" if unicodedata.category(char) not in HIDDEN_CATEGORIES)
    return " ".join(kept.split())
