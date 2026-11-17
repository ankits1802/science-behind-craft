from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.research.export_links import (
    EXPORT_LINK_SCHEMA_VERSION,
    EXPORT_LINK_SECONDS,
    EXPORT_MEDIA_TYPES,
    ExportLink,
)

from .naming import content_disposition, export_key
from .object_store import PresignedGet

__all__ = ["EXPORT_RENDERING", "ExportFile", "ExportObjects", "export_digest", "stored_export_link"]

EXPORT_RENDERING = "kalavigyan-export/v1"


class ExportObjects(Protocol):
    async def exists(self, key: str) -> bool: ...

    async def put(self, key: str, body: bytes, *, content_type: str) -> None: ...

    def presigned_get(self, key: str, *, disposition: str, seconds: int, now: datetime) -> PresignedGet: ...


@dataclass(frozen=True)
class ExportFile:
    owner_id: uuid.UUID
    fmt: str
    file_name: str
    made_from: Any


def export_digest(fmt: str, made_from: Any) -> str:
    canonical = json.dumps(
        [EXPORT_RENDERING, fmt, made_from], sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def stored_export_link(
    objects: ExportObjects, export: ExportFile, build: Callable[[], Awaitable[bytes]], *, now: datetime
) -> ExportLink:
    key = export_key(export.owner_id, export_digest(export.fmt, export.made_from), export.file_name)
    if not await objects.exists(key):
        await objects.put(key, await build(), content_type=EXPORT_MEDIA_TYPES[export.fmt])
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
