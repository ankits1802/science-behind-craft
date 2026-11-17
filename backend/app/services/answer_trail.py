from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from app.research.evidence import EvidenceItem, SourceDocument
from app.research.evidence_pack import PackedEvidence
from app.research.explainer import (
    PIECE_PREFIX,
    STORED_SOURCE_PREFIX,
    TRAIL_GROUP_OF_SOURCE,
    TRAIL_PUBLISHER_MAX_CHARS,
    TRAIL_STAGES,
    TRAIL_TITLE_MAX_CHARS,
)
from app.research.stream import Emit

__all__ = ["TrailLog", "piece_key", "stored_key"]

STORED_GROUP = "STORED"
STAGE_RANK = {stage: rank for rank, stage in enumerate(TRAIL_STAGES)}


def stored_key(source_id: str) -> str:
    return f"{STORED_SOURCE_PREFIX}:{source_id}"


def piece_key(piece_id: uuid.UUID) -> str:
    return f"{PIECE_PREFIX}:{piece_id}"


class TrailLog:
    def __init__(self, emit: Emit) -> None:
        self._emit = emit
        self._entries: dict[str, dict[str, Any]] = {}
        self._stages: dict[str, int] = {}

    async def found(self, evidence: Sequence[PackedEvidence]) -> None:
        for entry in evidence:
            await self._move(_evidence_entry(entry.item), "FOUND")

    async def read(self, document: SourceDocument) -> None:
        await self._move(_evidence_entry(document.item), "READ")

    async def found_stored(self, sources: Iterable[Mapping[str, Any]]) -> None:
        for source in sources:
            await self._move(_stored_entry(source), "FOUND")

    async def found_piece(self, piece_id: uuid.UUID, *, title: str, stored_at: datetime) -> None:
        entry = {
            "key": piece_key(piece_id),
            "group": STORED_GROUP,
            "title": title[:TRAIL_TITLE_MAX_CHARS],
            "url": None,
            "publisher": None,
            "year": None,
            "sourceId": None,
            "storedAt": stored_at,
        }
        await self._move(entry, "FOUND")

    async def quoted(self, evidence_ids: Iterable[str], sources: Iterable[Mapping[str, Any]]) -> None:
        for key in dict.fromkeys(evidence_ids):
            if key in self._entries:
                await self._move(self._entries[key], "QUOTED")
        for source in sources:
            await self._move(_stored_entry(source), "QUOTED")

    def knows(self, key: str) -> bool:
        return key in self._entries

    async def _move(self, entry: dict[str, Any], stage: str) -> None:
        key = entry["key"]
        if STAGE_RANK[stage] <= self._stages.get(key, -1):
            return
        self._entries.setdefault(key, entry)
        self._stages[key] = STAGE_RANK[stage]
        await self._emit("trail", {**self._entries[key], "stage": stage})


def _evidence_entry(item: EvidenceItem) -> dict[str, Any]:
    return {
        "key": item.id,
        "group": TRAIL_GROUP_OF_SOURCE[item.source_type],
        "title": item.title[:TRAIL_TITLE_MAX_CHARS],
        "url": item.url,
        "publisher": item.publisher[:TRAIL_PUBLISHER_MAX_CHARS] if item.publisher else None,
        "year": int(item.published[:4]) if item.published else None,
        "sourceId": None,
        "storedAt": None,
    }


def _stored_entry(source: Mapping[str, Any]) -> dict[str, Any]:
    publisher = source.get("publisher")
    return {
        "key": stored_key(str(source["id"])),
        "group": STORED_GROUP,
        "title": str(source["title"])[:TRAIL_TITLE_MAX_CHARS],
        "url": source.get("url"),
        "publisher": str(publisher)[:TRAIL_PUBLISHER_MAX_CHARS] if publisher else None,
        "year": source.get("year"),
        "sourceId": str(source["id"]),
        "storedAt": None,
    }
