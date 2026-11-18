from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http_cache import body_version
from app.models import Craft, CraftPageArchive, CraftPageSnapshot, CuratedCraft

__all__ = [
    "FIELD_VOICE_KINDS",
    "archive_superseded",
    "archived_page",
    "curation_version",
    "without_field_voices",
]

FIELD_VOICE_KINDS = frozenset({"artisan_voice", "field_photos"})
NO_FIELD_VOICES = {"quotes": 0, "images": 0}
SOURCE_LIST = "source_list"


async def curation_version(session: AsyncSession, craft: Craft) -> int | None:
    found: int | None = await session.scalar(
        select(CuratedCraft.version).where(CuratedCraft.craftId == craft.id)
    )
    return found


async def archived_page(
    session: AsyncSession, craft: Craft, variant: str, version: int
) -> dict[str, Any] | None:
    row = await session.get(CraftPageArchive, (craft.id, version, variant))
    return without_field_voices(row.body) if row is not None else None


async def archive_superseded(
    session: AsyncSession, stored: CraftPageSnapshot, now_version: int | None, *, at: datetime
) -> None:
    before = _version(stored.body)
    if before is None or before == now_version:
        return
    body = without_field_voices(stored.body)
    statement = insert(CraftPageArchive).values(
        craftId=stored.craftId,
        curationVersion=before,
        variant=stored.variant,
        body=body,
        etag=body_version(body),
        frozenAt=at,
    )
    await session.execute(statement.on_conflict_do_nothing())


def without_field_voices(body: Mapping[str, Any]) -> dict[str, Any]:
    chapters = []
    voiced: set[str] = set(_source_ids(body.get("voices") or []))
    for chapter in body.get("chapters") or []:
        items = []
        for item in chapter["items"]:
            if _item_kind(item) in FIELD_VOICE_KINDS:
                voiced.update(_source_ids(item))
            else:
                items.append(item)
        if items:
            chapters.append({**chapter, "items": items})
    kept = {
        **body,
        "chapters": chapters,
        "voices": [],
        "fieldPhotos": [],
        "fieldVoicesTotal": NO_FIELD_VOICES,
    }
    gone = voiced - set(_source_ids({key: value for key, value in kept.items() if key != "sources"}))
    listed = [_without_sources(chapter, gone) for chapter in chapters]
    return {
        **kept,
        "chapters": [chapter for chapter in listed if chapter["items"]],
        "sources": [source for source in body.get("sources") or [] if source.get("id") not in gone],
    }


def _item_kind(item: Mapping[str, Any]) -> str | None:
    piece = item.get("block") or item.get("part") or {}
    kind = piece.get("kind")
    return kind if isinstance(kind, str) else None


def _without_sources(chapter: Mapping[str, Any], gone: set[str]) -> dict[str, Any]:
    if not gone:
        return dict(chapter)
    items = []
    for item in chapter["items"]:
        part = item.get("part")
        if part is None or part.get("kind") != SOURCE_LIST:
            items.append(item)
            continue
        groups = [
            {**group, "sourceIds": [sid for sid in group["sourceIds"] if sid not in gone]}
            for group in part["groups"]
        ]
        kept = [group for group in groups if group["sourceIds"]]
        if kept:
            items.append({**item, "part": {**part, "groups": kept}})
    return {**chapter, "items": items}


def _source_ids(value: Any) -> Iterator[str]:
    if isinstance(value, Mapping):
        for key, inner in value.items():
            if key == "sourceId" and isinstance(inner, str):
                yield inner
            else:
                yield from _source_ids(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _source_ids(inner)


def _version(body: Mapping[str, Any]) -> int | None:
    curation = body.get("curation")
    version = curation.get("version") if isinstance(curation, Mapping) else None
    return version if isinstance(version, int) else None
