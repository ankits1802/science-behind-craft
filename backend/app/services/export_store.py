from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from app.core.errors import AppError
from app.research.export_links import (
    EXPORT_LINK_SCHEMA_VERSION,
    EXPORT_LINK_SECONDS,
    EXPORT_MEDIA_TYPES,
    ExportLink,
)

from .naming import content_disposition, export_key
from .object_store import PresignedGet

__all__ = [
    "BUILDS_BUSY",
    "BUILD_WAIT_SECONDS",
    "BUSY_RETRY_SECONDS",
    "EXPORT_BUILDS_AT_ONCE",
    "EXPORT_RENDERING",
    "UNREAD_REUSED_FOR",
    "Admission",
    "BuildRefused",
    "BuildsBusy",
    "BuildsSpent",
    "BuiltExport",
    "ExportFile",
    "ExportObjects",
    "WaitedSlots",
    "export_digest",
    "stored_export_link",
]

EXPORT_RENDERING = "kalavigyan-export/v1"
EXPORT_BUILDS_AT_ONCE = 2
BUILD_WAIT_SECONDS = 5.0
BUSY_RETRY_SECONDS = 30.0
BUILDS_BUSY = "Other files are being made just now. Try again in half a minute."
UNREAD_REUSED_FOR = timedelta(hours=1)

Admission = Callable[[], Awaitable[None]]


class ExportObjects(Protocol):
    async def exists(self, key: str) -> bool: ...

    async def put(self, key: str, body: bytes, *, content_type: str) -> None: ...

    async def delete(self, key: str) -> None: ...

    def presigned_get(self, key: str, *, disposition: str, seconds: int, now: datetime) -> PresignedGet: ...


class BuildRefused(AppError):
    def __init__(self, message: str, *, retry_after: float) -> None:
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


class BuildsBusy(BuildRefused):
    pass


class BuildsSpent(BuildRefused):
    pass


class WaitedSlots(asyncio.Semaphore):
    def __init__(self, value: int, *, wait_seconds: float, retry_after: float) -> None:
        super().__init__(value)
        self.wait_seconds = wait_seconds
        self.retry_after = retry_after

    async def __aenter__(self) -> None:
        try:
            async with asyncio.timeout(self.wait_seconds):
                await self.acquire()
        except TimeoutError:
            raise BuildsBusy(BUILDS_BUSY, retry_after=self.retry_after) from None


@dataclass(frozen=True)
class ExportFile:
    owner_id: uuid.UUID
    fmt: str
    file_name: str
    made_from: Any
    stored_name: str | None = None
    unread_reused_for: timedelta | None = None

    def key(self) -> str:
        return self._key(self.made_from)

    def unread_key(self, unread: frozenset[uuid.UUID], now: datetime) -> str:
        if self.unread_reused_for is None:
            return self._key({"madeFrom": self.made_from, "unread": sorted(str(one) for one in unread)})
        return self._unread_window_key(self.unread_reused_for, now)

    def reusable_keys(self, now: datetime) -> tuple[str, ...]:
        if self.unread_reused_for is None:
            return (self.key(),)
        return self.key(), self._unread_window_key(self.unread_reused_for, now)

    def _unread_window_key(self, window: timedelta, now: datetime) -> str:
        return self._key({"madeFrom": self.made_from, "unreadFrom": _window_start(now, window).isoformat()})

    def _key(self, made_from: Any) -> str:
        return export_key(
            self.owner_id, export_digest(self.fmt, made_from), self.stored_name or self.file_name
        )


@dataclass(frozen=True)
class BuiltExport:
    body: bytes
    unread: frozenset[uuid.UUID] = frozenset()


def export_digest(fmt: str, made_from: Any) -> str:
    canonical = json.dumps(
        [EXPORT_RENDERING, fmt, made_from], sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def stored_export_link(
    objects: ExportObjects,
    export: ExportFile,
    build: Callable[[], Awaitable[BuiltExport]],
    *,
    now: datetime,
    builds: asyncio.Semaphore,
    admit: Admission | None = None,
) -> ExportLink:
    key = await _found(objects, export, now)
    if key is None:
        if admit is not None:
            await admit()
        key = await _filed(objects, export, build, now=now, builds=builds)
    link = objects.presigned_get(
        key,
        disposition=content_disposition(export.file_name, inline=False),
        seconds=EXPORT_LINK_SECONDS,
        now=now,
    )
    return ExportLink(
        schema_version=EXPORT_LINK_SCHEMA_VERSION,
        format=export.fmt,
        file_name=export.file_name,
        url=link.url,
        expires_at=link.expires_at,
    )


async def _found(objects: ExportObjects, export: ExportFile, now: datetime) -> str | None:
    for key in export.reusable_keys(now):
        if await objects.exists(key):
            return key
    return None


async def _filed(
    objects: ExportObjects,
    export: ExportFile,
    build: Callable[[], Awaitable[BuiltExport]],
    *,
    now: datetime,
    builds: asyncio.Semaphore,
) -> str:
    async with builds:
        found = await _found(objects, export, now)
        if found is not None:
            return found
        built = await build()
        key = export.unread_key(built.unread, now) if built.unread else export.key()
        await objects.put(key, built.body, content_type=EXPORT_MEDIA_TYPES[export.fmt])
    return key


def _window_start(now: datetime, window: timedelta) -> datetime:
    seconds = window.total_seconds()
    return datetime.fromtimestamp(now.timestamp() // seconds * seconds, UTC)
