from __future__ import annotations

import re

import httpx

from app.core.config import Settings
from app.core.errors import InvalidInput, NotConfigured
from app.services.field_voices_feed import (
    IMAGES,
    STREAMS,
    VIEWS,
    FieldVoicesPage,
    FieldVoicesState,
    Live,
    image_host,
    parse_page,
    parse_state,
)
from app.services.field_voices_items import ImageItem
from app.services.field_voices_screen import PortalScreen
from app.services.portal_peer import PortalPeer, peer_for

__all__ = [
    "IMAGE_HOSTS_SETTING",
    "REQUESTED_BY",
    "STATE_ROUTE",
    "FieldVoicesReader",
    "field_voices_reader",
    "image_hosts",
    "stream_route",
]

STATE_ROUTE = "/field-voices"
REQUESTED_BY = "kalavigyan-field-voices"
WHAT = "field voices"
IMAGE_HOSTS_SETTING = "FIELD_VOICES_IMAGE_HOSTS"
HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
HOST_PATTERN = re.compile(rf"^(?=.{{1,253}}$){HOST_LABEL}(?:\.{HOST_LABEL})+$")


def stream_route(stream: str) -> str:
    if stream not in STREAMS:
        raise InvalidInput(f"No field voices stream is called {stream!r}")
    return f"{STATE_ROUTE}/{stream}"


class FieldVoicesReader:
    def __init__(self, peer: PortalPeer, *, image_hosts: frozenset[str]) -> None:
        self._peer = peer
        self._image_hosts = image_hosts

    @property
    def portal(self) -> str:
        return self._peer.portal

    async def state(self) -> FieldVoicesState:
        payload = await self._peer.signed_json(STATE_ROUTE, what=f"{WHAT} state", requested_by=REQUESTED_BY)
        return parse_state(payload, portal=self.portal)

    async def page(
        self, stream: str, view: str, cursor: str | None, *, screen: PortalScreen
    ) -> FieldVoicesPage:
        if view not in VIEWS:
            raise InvalidInput(f"No field voices view is called {view!r}")
        params = {"view": view} | ({"cursor": cursor} if cursor is not None else {})
        payload = await self._peer.signed_json(
            stream_route(stream), what=f"{WHAT} {stream}", requested_by=REQUESTED_BY, params=params
        )
        page = parse_page(payload, portal=self.portal, asked=(stream, view, cursor), screen=screen)
        if stream == IMAGES:
            self._refuse_other_hosts(page)
        return page

    def _refuse_other_hosts(self, page: FieldVoicesPage) -> None:
        for change in page.changes:
            item = change.item if isinstance(change, Live) else None
            if isinstance(item, ImageItem) and image_host(item) not in self._image_hosts:
                raise InvalidInput(
                    f"{page.portal} image {change.id} is served from a host "
                    f"that {IMAGE_HOSTS_SETTING} does not list"
                )


def field_voices_reader(
    settings: Settings, portal: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> FieldVoicesReader:
    if not settings.field_voices_enabled:
        raise NotConfigured(
            "FIELD_VOICES_ENABLED", "FIELD_VOICES_ENABLED is off, so field voices are not read"
        )
    peer = peer_for(settings, portal, transport=transport)
    return FieldVoicesReader(peer, image_hosts=image_hosts(settings.field_voices_image_hosts))


def image_hosts(listed: str | None) -> frozenset[str]:
    hosts = frozenset(host.strip().lower() for host in (listed or "").split(",") if host.strip())
    if not hosts or not all(HOST_PATTERN.match(host) for host in hosts):
        raise NotConfigured(
            IMAGE_HOSTS_SETTING,
            f"{IMAGE_HOSTS_SETTING} must list the bare host names the portals' images are served from",
        )
    return hosts
