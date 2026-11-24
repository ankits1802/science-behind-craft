from __future__ import annotations

import httpx
from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.research.open_pictures import COMMONS, FLICKR, OpenLink, OpenPictureRecord, open_link

from ..adapter import Clock, utc_now
from ..http import RatePolicy, ResponseCache, SourceHttp
from ..records import UnusableRecord
from ..reference.commons import COMMONS_RATE, WikimediaCommonsAdapter
from .flickr import FLICKR_RATE, FlickrPhotos
from .openverse import OPENVERSE_RATE, OpenverseAdapter

__all__ = ["OpenPicturePages", "home_link", "open_picture_pages"]

HOMES = frozenset({COMMONS, FLICKR})
UNREADABLE = "The record of {url} could not be read: {why}"


class OpenPicturePages:
    def __init__(
        self, commons: WikimediaCommonsAdapter, openverse: OpenverseAdapter, flickr: FlickrPhotos
    ) -> None:
        self.commons = commons
        self.openverse = openverse
        self.flickr = flickr

    async def record(self, link: OpenLink) -> OpenPictureRecord:
        try:
            return await self._read(link)
        except (UnusableRecord, ValidationError) as unread:
            raise InvalidInput(UNREADABLE.format(url=link.url, why=unread)) from None

    async def _read(self, link: OpenLink) -> OpenPictureRecord:
        if link.site == COMMONS:
            return await self.commons.picture(link.key)
        if link.site == FLICKR:
            return await self.flickr.picture(link.url)
        indexed = await self.openverse.picture(link.key)
        home = home_link(indexed)
        return indexed if home is None else await self._read(home)


def home_link(indexed: OpenPictureRecord) -> OpenLink | None:
    for address in (indexed.page_url, indexed.file_url):
        try:
            found = open_link(address)
        except InvalidInput:
            continue
        if found.site in HOMES:
            return found
    return None


def open_picture_pages(client: httpx.AsyncClient, *, clock: Clock = utc_now) -> OpenPicturePages:
    def http(service: str, policy: RatePolicy) -> SourceHttp:
        return SourceHttp(client=client, service=service, policy=policy, cache=ResponseCache(max_entries=0))

    return OpenPicturePages(
        WikimediaCommonsAdapter(http(WikimediaCommonsAdapter.name, COMMONS_RATE), clock=clock),
        OpenverseAdapter(http(OpenverseAdapter.name, OPENVERSE_RATE), clock=clock),
        FlickrPhotos(http(FlickrPhotos.name, FLICKR_RATE), clock=clock),
    )
