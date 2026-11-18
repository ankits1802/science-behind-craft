from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import AwareDatetime, Field, ValidationError

from app.core.errors import InvalidInput
from app.services.field_voices_items import ImageItem, TranscriptItem
from app.services.field_voices_never_sent import forbidden_keys
from app.services.portal_craft_feed import FeedModel, Portal, first_problem

__all__ = [
    "FIELD_VOICES_SCHEMA_VERSION",
    "GONE_REASONS",
    "IMAGES",
    "SIGNED_URL_MAX_LIFE",
    "STREAMS",
    "TRANSCRIPTS",
    "VIEWS",
    "VIEW_ALL",
    "VIEW_GONE",
    "FieldVoicesPage",
    "FieldVoicesState",
    "Gone",
    "Live",
    "Screen",
    "StreamState",
    "image_host",
    "item_revision",
    "parse_page",
    "parse_state",
    "stream_digest",
]

FIELD_VOICES_SCHEMA_VERSION = 2
TRANSCRIPTS = "transcripts"
IMAGES = "images"
STREAMS = (TRANSCRIPTS, IMAGES)
VIEW_ALL = "all"
VIEW_GONE = "gone"
VIEWS = (VIEW_ALL, VIEW_GONE)
GONE_REASONS = ("DELETED", "WITHDRAWN", "REPLACED", "MERGED", "UNLISTED")
SUCCEEDED_REASONS = ("REPLACED", "MERGED")
LIVE = "LIVE"
GONE = "GONE"
REVISION_CHARS = 32
SIGNED_URL_MAX_LIFE = timedelta(minutes=15)
CLOCK_SKEW = timedelta(minutes=2)
UNSIGNED_ITEM_KEYS = ("state", "revision", "updatedAt")
UNSIGNED_IMAGE_KEYS = ("url", "expiresAt")
PAGE_LIMITS = {TRANSCRIPTS: 20, IMAGES: 100}
ITEM_MODELS: Mapping[str, type[TranscriptItem] | type[ImageItem]] = {
    TRANSCRIPTS: TranscriptItem,
    IMAGES: ImageItem,
}

Screen = Callable[[str, dict[str, Any]], dict[str, Any]]


class StreamState(FeedModel):
    enabled: bool
    live: int = Field(ge=0)
    gone: int = Field(ge=0)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    latest_cursor: str | None = Field(default=None, min_length=1, max_length=512)


class StreamStates(FeedModel):
    transcripts: StreamState
    images: StreamState


class FieldVoicesState(FeedModel):
    schema_version: Literal[2]
    portal: Portal
    generated_at: AwareDatetime
    refreshed_at: AwareDatetime | None = None
    streams: StreamStates

    def stream(self, name: str) -> StreamState:
        return self.streams.transcripts if name == TRANSCRIPTS else self.streams.images


class _PageEnvelope(FeedModel):
    schema_version: Literal[2]
    portal: Portal
    generated_at: AwareDatetime
    stream: Literal[*STREAMS]
    view: Literal[*VIEWS]
    cursor: str | None = Field(default=None, min_length=1, max_length=512)
    next_cursor: str | None = Field(default=None, min_length=1, max_length=512)
    has_more: bool
    changes: list[dict[str, Any]]


class _Header(FeedModel):
    state: Literal[LIVE, GONE]
    id: str = Field(min_length=1, max_length=64, pattern=r"^\S+$")
    updated_at: AwareDatetime
    revision: str | None = Field(default=None, pattern=rf"^[0-9a-f]{{{REVISION_CHARS}}}$")
    reason: Literal[*GONE_REASONS] | None = None
    successor_id: str | None = Field(default=None, min_length=1, max_length=64)


@dataclass(frozen=True)
class Live:
    id: str
    updated_at: datetime
    revision: str
    item: TranscriptItem | ImageItem


@dataclass(frozen=True)
class Gone:
    id: str
    updated_at: datetime
    reason: str
    successor_id: str | None


@dataclass(frozen=True)
class FieldVoicesPage:
    portal: str
    stream: str
    view: str
    generated_at: datetime
    cursor: str | None
    next_cursor: str | None
    has_more: bool
    changes: tuple[Live | Gone, ...]


def parse_state(payload: Any, *, portal: str) -> FieldVoicesState:
    state = _validated(FieldVoicesState, _checked(payload, portal, "field voices state"), what="state")
    _refuse_other_portal(state.portal, portal, "state")
    return state


def parse_page(
    payload: Any,
    *,
    portal: str,
    asked: tuple[str, str, str | None],
    screen: Screen | None = None,
) -> FieldVoicesPage:
    stream, view, cursor = asked
    raw = _checked(payload, portal, f"{stream} page")
    page = _validated(_PageEnvelope, raw, what=f"{stream} page")
    _refuse_other_portal(page.portal, portal, f"{stream} page")
    if (page.stream, page.view, page.cursor) != (stream, view, cursor):
        raise InvalidInput(
            f"{portal} answered {page.stream}/{page.view} at cursor {page.cursor!r} "
            f"when asked for {stream}/{view} at cursor {cursor!r}"
        )
    if len(page.changes) > PAGE_LIMITS[stream]:
        raise InvalidInput(f"{portal} sent {len(page.changes)} {stream} changes, over {PAGE_LIMITS[stream]}")
    changes = tuple(_change(change, page, screen) for change in page.changes)
    _refuse_out_of_order(portal, stream, changes)
    if not changes and page.next_cursor != cursor:
        raise InvalidInput(f"{portal} moved the {stream} cursor on an empty page")
    if changes and page.next_cursor is None:
        raise InvalidInput(f"{portal} sent {stream} changes without the cursor after them")
    return FieldVoicesPage(
        portal=page.portal,
        stream=stream,
        view=view,
        generated_at=page.generated_at,
        cursor=page.cursor,
        next_cursor=page.next_cursor,
        has_more=page.has_more,
        changes=changes,
    )


def item_revision(raw_item: Mapping[str, Any]) -> str:
    signed = {key: value for key, value in raw_item.items() if key not in UNSIGNED_ITEM_KEYS}
    image = signed.get("image")
    if isinstance(image, dict):
        signed["image"] = {key: value for key, value in image.items() if key not in UNSIGNED_IMAGE_KEYS}
    text = json.dumps(signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:REVISION_CHARS]


def stream_digest(live: Iterable[tuple[str, str]]) -> str:
    lines = sorted(f"{item_id} {revision}\n" for item_id, revision in live)
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def _checked(payload: Any, portal: str, what: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InvalidInput(f"{portal} {what} is not a JSON object")
    version = payload.get("schemaVersion")
    if version != FIELD_VOICES_SCHEMA_VERSION:
        raise InvalidInput(
            f"{portal} {what} has schemaVersion {version!r}; this build reads {FIELD_VOICES_SCHEMA_VERSION}"
        )
    refused = forbidden_keys(payload)
    if refused:
        raise InvalidInput(
            f"{portal} {what} carries fields that are never sent: {', '.join(sorted(refused))}"
        )
    return payload


def _validated[T: FeedModel](model: type[T], payload: Any, *, what: str) -> T:
    try:
        return model.model_validate(payload)
    except ValidationError as error:
        raise InvalidInput(f"the field voices {what} breaks the contract: {first_problem(error)}") from None


def _refuse_other_portal(answered: str, asked: str, what: str) -> None:
    if answered != asked:
        raise InvalidInput(f"the {asked} address answered with a {what} from {answered}")


def _change(raw: dict[str, Any], page: _PageEnvelope, screen: Screen | None) -> Live | Gone:
    header = _validated(_Header, raw, what=f"{page.stream} change")
    if header.state == GONE:
        return _gone(header, raw)
    if page.view == VIEW_GONE:
        raise InvalidInput(f"{page.portal} listed live item {header.id} in the gone view")
    if header.revision is None or header.reason is not None or header.successor_id is not None:
        raise InvalidInput(f"{page.portal} live item {header.id} needs a revision and no reason")
    if item_revision(raw) != header.revision:
        raise InvalidInput(f"{page.portal} item {header.id} does not match its revision {header.revision}")
    shown = screen(page.stream, copy.deepcopy(raw)) if screen is not None else raw
    item = _validated(ITEM_MODELS[page.stream], shown, what=f"{page.stream} item {header.id}")
    if item.id != header.id:
        raise InvalidInput(f"{page.portal} change {header.id} carries item {item.id}")
    if isinstance(item, ImageItem):
        _refuse_stale_link(item, page.generated_at)
    return Live(id=header.id, updated_at=header.updated_at, revision=header.revision, item=item)


def _gone(header: _Header, raw: dict[str, Any]) -> Gone:
    extra = set(raw) - {"state", "id", "updatedAt", "reason", "successorId"}
    if extra or header.revision is not None or header.reason is None:
        raise InvalidInput(f"tombstone {header.id} carries content or lacks its reason")
    if (header.successor_id is not None) != (header.reason in SUCCEEDED_REASONS):
        raise InvalidInput(f"tombstone {header.id}: a successor comes exactly with REPLACED or MERGED")
    return Gone(
        id=header.id, updated_at=header.updated_at, reason=header.reason, successor_id=header.successor_id
    )


def _refuse_stale_link(item: ImageItem, generated_at: datetime) -> None:
    latest = generated_at + SIGNED_URL_MAX_LIFE + CLOCK_SKEW
    if not generated_at < item.image.expires_at <= latest:
        raise InvalidInput(f"image {item.id} has a signed URL outside the 15 minutes allowed")


def _refuse_out_of_order(portal: str, stream: str, changes: tuple[Live | Gone, ...]) -> None:
    for before, after in pairwise(changes):
        if (after.updated_at, after.id) <= (before.updated_at, before.id):
            raise InvalidInput(f"{portal} {stream} changes are out of order at {after.id}")


def image_host(item: ImageItem) -> str:
    return (urlsplit(item.image.url).hostname or "").lower()
