from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import InvalidInput, NotConfigured, Refused
from app.research.evidence import personal_data_in
from app.services.field_voices_feed import (
    ArtisanCredit,
    FieldPhotograph,
    FieldRecording,
    FieldVoicesEntry,
    FieldVoicesIndex,
    PhotographsPage,
    QuotesPage,
    parse_index,
    parse_photographs_page,
    parse_quotes_page,
    snapshot_digest,
)
from app.services.portal_craft_feed import FIELD_REPOSITORY, refuse_duplicates
from app.services.portal_peer import PortalPeer, peer_for

__all__ = [
    "IMAGE_HOSTS_SETTING",
    "INDEX_ROUTE",
    "MAX_PAGES",
    "REQUESTED_BY",
    "CraftVoices",
    "DroppedItem",
    "FieldVoicesReader",
    "field_voices_reader",
    "photographs_route",
    "quotes_route",
]

INDEX_ROUTE = "/field-voices"
REQUESTED_BY = "kalavigyan-field-voices"
WHAT = "field voices"
MAX_PAGES = 200
CURSOR_PARAM = "cursor"
QUOTE = "quote"
RECORDING = "recording"
PHOTOGRAPH = "photograph"
IMAGE_HOSTS_SETTING = "FIELD_VOICES_IMAGE_HOSTS"
HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
HOST_PATTERN = re.compile(rf"^(?=.{{1,253}}$){HOST_LABEL}(?:\.{HOST_LABEL})+$")
UNTIMED = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class DroppedItem:
    kind: str
    item_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CraftVoices:
    craft_slug: str
    digest: str
    recordings: tuple[FieldRecording, ...]
    photographs: tuple[FieldPhotograph, ...]
    dropped: tuple[DroppedItem, ...]


def quotes_route(craft_slug: str) -> str:
    return f"{INDEX_ROUTE}/{craft_slug}/quotes"


def photographs_route(craft_slug: str) -> str:
    return f"{INDEX_ROUTE}/{craft_slug}/photographs"


class FieldVoicesReader:
    def __init__(self, peer: PortalPeer, *, image_hosts: frozenset[str], max_pages: int = MAX_PAGES) -> None:
        self._peer = peer
        self._image_hosts = image_hosts
        self._max_pages = max_pages

    @property
    def portal(self) -> str:
        return self._peer.portal

    async def index(self) -> FieldVoicesIndex:
        payload = await self._peer.signed_json(INDEX_ROUTE, what=f"{WHAT} index", requested_by=REQUESTED_BY)
        return parse_index(payload, portal=self.portal)

    async def craft(self, entry: FieldVoicesEntry) -> CraftVoices:
        slug = entry.craft_slug
        recordings = await self._recordings(entry)
        photographs = await self._photographs(entry)
        _refuse_changed_snapshot(entry, recordings, photographs)
        _refuse_out_of_order(slug, recordings, photographs)
        kept_recordings, dropped = _screened_recordings(recordings)
        kept_photographs, dropped_photographs = _screened_photographs(photographs)
        return CraftVoices(
            craft_slug=slug,
            digest=entry.digest,
            recordings=kept_recordings,
            photographs=kept_photographs,
            dropped=(*dropped, *dropped_photographs),
        )

    async def _recordings(self, entry: FieldVoicesEntry) -> tuple[FieldRecording, ...]:
        if entry.recordings == 0:
            return ()
        slug = entry.craft_slug
        pages = await self._pages(quotes_route(slug), self._quotes_parser(slug))
        return tuple(r for page in pages for r in page.recordings)

    async def _photographs(self, entry: FieldVoicesEntry) -> tuple[FieldPhotograph, ...]:
        if entry.photographs == 0:
            return ()
        slug = entry.craft_slug
        pages = await self._pages(photographs_route(slug), self._photographs_parser(slug))
        return tuple(p for page in pages for p in page.photographs)

    async def _pages[P](self, route: str, parse: Callable[[Any, str | None], P]) -> list[P]:
        pages: list[P] = []
        cursor: str | None = None
        asked: set[str] = set()
        for _ in range(self._max_pages):
            params = {CURSOR_PARAM: cursor} if cursor is not None else None
            payload = await self._peer.signed_json(route, what=WHAT, requested_by=REQUESTED_BY, params=params)
            page = parse(payload, cursor)
            pages.append(page)
            cursor = page.next_cursor
            if cursor is None:
                return pages
            if cursor in asked:
                raise InvalidInput(f"{self.portal} {route} pages loop back to cursor {cursor!r}")
            asked.add(cursor)
        raise InvalidInput(f"{self.portal} {route} runs past {self._max_pages} pages")

    def _quotes_parser(self, slug: str) -> Callable[[Any, str | None], QuotesPage]:
        def parse(payload: Any, cursor: str | None) -> QuotesPage:
            return parse_quotes_page(payload, portal=self.portal, craft_slug=slug, cursor=cursor)

        return parse

    def _photographs_parser(self, slug: str) -> Callable[[Any, str | None], PhotographsPage]:
        def parse(payload: Any, cursor: str | None) -> PhotographsPage:
            return parse_photographs_page(
                payload, portal=self.portal, craft_slug=slug, cursor=cursor, image_hosts=self._image_hosts
            )

        return parse


def field_voices_reader(
    settings: Settings,
    *,
    portal: str = FIELD_REPOSITORY,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FieldVoicesReader:
    if not settings.field_voices_enabled:
        raise NotConfigured(
            "FIELD_VOICES_ENABLED", "FIELD_VOICES_ENABLED is off, so field voices are not read"
        )
    peer = peer_for(settings, portal, transport=transport)
    return FieldVoicesReader(peer, image_hosts=_image_hosts(settings.field_voices_image_hosts))


def _image_hosts(listed: str | None) -> frozenset[str]:
    hosts = frozenset(host.strip().lower() for host in (listed or "").split(",") if host.strip())
    if not hosts or not all(HOST_PATTERN.match(host) for host in hosts):
        raise NotConfigured(
            IMAGE_HOSTS_SETTING,
            f"{IMAGE_HOSTS_SETTING} must list the bare host names the portal's photographs are served from",
        )
    return hosts


def _refuse_changed_snapshot(
    entry: FieldVoicesEntry,
    recordings: tuple[FieldRecording, ...],
    photographs: tuple[FieldPhotograph, ...],
) -> None:
    try:
        refuse_duplicates(f"{entry.craft_slug} recording", [r.id for r in recordings])
        refuse_duplicates(f"{entry.craft_slug} photograph", [p.id for p in photographs])
    except ValueError as error:
        raise InvalidInput(str(error)) from None
    quotes = sum(len(r.quotes) for r in recordings)
    read = (len(recordings), quotes, len(photographs))
    listed = (entry.recordings, entry.quotes, entry.photographs)
    if read != listed or snapshot_digest(recordings, photographs) != entry.digest:
        raise Refused(
            "snapshot_changed",
            f"{entry.craft_slug} changed while it was read: listed {listed} with digest {entry.digest}, "
            f"read {read}; nothing of it is applied this run",
        )


def _refuse_out_of_order(
    slug: str, recordings: tuple[FieldRecording, ...], photographs: tuple[FieldPhotograph, ...]
) -> None:
    _refuse_backwards(f"{slug} recordings", [(r.recorded_at, r.id) for r in recordings])
    _refuse_backwards(
        f"{slug} photographs", [(p.taken_at is None, p.taken_at or UNTIMED, p.id) for p in photographs]
    )


def _refuse_backwards(what: str, keys: list[tuple[Any, ...]]) -> None:
    for before, after in pairwise(keys):
        if after < before:
            raise InvalidInput(
                f"{what} are out of the contract's order: {after[-1]} comes after {before[-1]}"
            )


def _screened_recordings(
    recordings: tuple[FieldRecording, ...],
) -> tuple[tuple[FieldRecording, ...], list[DroppedItem]]:
    kept: list[FieldRecording] = []
    dropped: list[DroppedItem] = []
    for recording in recordings:
        reasons = _personal_data(_recording_texts(recording))
        if reasons:
            dropped.append(DroppedItem(RECORDING, recording.id, reasons))
            continue
        screened, dropped_quotes = _screened_quotes(recording)
        dropped += dropped_quotes
        if screened is not None:
            kept.append(_untitled_beside_unnamed(screened))
    return tuple(kept), dropped


def _screened_quotes(recording: FieldRecording) -> tuple[FieldRecording | None, list[DroppedItem]]:
    quotes = []
    dropped: list[DroppedItem] = []
    for quote in recording.quotes:
        found = _personal_data((quote.text, quote.english or ""))
        if found:
            dropped.append(DroppedItem(QUOTE, quote.id, found))
        else:
            quotes.append(quote)
    if not quotes:
        return None, dropped
    if not dropped:
        return recording, dropped
    speakers = {q.artisan_id for q in quotes}
    artisans = tuple(a for a in recording.artisans if a.id in speakers)
    return recording.model_copy(update={"quotes": tuple(quotes), "artisans": artisans}), dropped


def _screened_photographs(
    photographs: tuple[FieldPhotograph, ...],
) -> tuple[tuple[FieldPhotograph, ...], list[DroppedItem]]:
    kept: list[FieldPhotograph] = []
    dropped: list[DroppedItem] = []
    for photograph in photographs:
        reasons = _personal_data(_photograph_texts(photograph))
        if reasons:
            dropped.append(DroppedItem(PHOTOGRAPH, photograph.id, reasons))
        else:
            kept.append(_untitled_beside_unnamed(photograph))
    return tuple(kept), dropped


def _untitled_beside_unnamed[I: (FieldRecording, FieldPhotograph)](item: I) -> I:
    workshop = item.workshop
    if workshop is None or workshop.title is None or all(a.named for a in item.artisans):
        return item
    return item.model_copy(update={"workshop": workshop.model_copy(update={"title": None})})


def _recording_texts(recording: FieldRecording) -> list[str]:
    texts = _credit_texts(recording.artisans)
    if recording.workshop:
        texts.append(recording.workshop.title)
    for topic in recording.topics:
        texts += [topic.section_title, topic.question or ""]
    return texts


def _photograph_texts(photograph: FieldPhotograph) -> list[str]:
    texts = [*_credit_texts(photograph.artisans), photograph.caption or ""]
    if photograph.workshop:
        texts.append(photograph.workshop.title)
    if photograph.stage:
        texts += [photograph.stage.process, photograph.stage.step]
    return texts


def _credit_texts(artisans: tuple[ArtisanCredit, ...]) -> list[str]:
    return [text for a in artisans for text in (a.name, a.local_name) if text]


def _personal_data(texts: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    found = {label for text in texts if text for label in personal_data_in(text)}
    return tuple(sorted(found))
