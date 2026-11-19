from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk
from app.research.retrieval import PUBLIC_CHUNK_ACL
from app.retrieval.indexing import SourceChunk, replace_planned_chunks

from .claim_seed import seed_id

__all__ = [
    "LOCATOR_MAX_CHARS",
    "LOCATOR_SEPARATOR",
    "PASSED_QUOTE_CHECK",
    "SEED_PASSAGE_ACL",
    "SEED_PASSAGE_LANG",
    "SeedPassages",
    "seed_passages",
    "store_seed_passages",
]

PASSED_QUOTE_CHECK = "PASS"
SEED_PASSAGE_ACL = PUBLIC_CHUNK_ACL
SEED_PASSAGE_LANG = "en"
LOCATOR_SEPARATOR = "; "
LOCATOR_MAX_CHARS: int = Chunk.__table__.c.locator.type.length


@dataclass(frozen=True)
class SeedPassages:
    source_id: uuid.UUID
    chunks: tuple[SourceChunk, ...]


def seed_passages(data: Mapping[str, Any]) -> list[SeedPassages]:
    quoted: dict[str, dict[str, list[str]]] = {}
    for claim in data.get("claims") or []:
        for cite in claim.get("sources") or []:
            quote = (cite.get("quote") or "").strip()
            if not quote or cite.get("quoteCheck") != PASSED_QUOTE_CHECK:
                continue
            locators = quoted.setdefault(cite["sourceId"], {}).setdefault(quote, [])
            locator = (cite.get("locator") or "").strip()
            if locator and locator not in locators:
                locators.append(locator)
    return [
        SeedPassages(
            source_id=seed_id("source", source_key),
            chunks=tuple(_chunk(quote, locators) for quote, locators in quotes.items()),
        )
        for source_key, quotes in quoted.items()
    ]


async def store_seed_passages(session: AsyncSession, data: Mapping[str, Any]) -> int:
    planned = seed_passages(data)
    kept = await _sources_with_chunks(session, [passages.source_id for passages in planned])
    stored = 0
    for passages in planned:
        if passages.source_id not in kept:
            stored += await replace_planned_chunks(session, passages.source_id, passages.chunks)
    return stored


def _chunk(quote: str, locators: Sequence[str]) -> SourceChunk:
    locator = LOCATOR_SEPARATOR.join(locators)[:LOCATOR_MAX_CHARS]
    return SourceChunk(text=quote, locator=locator, lang=SEED_PASSAGE_LANG, acl=SEED_PASSAGE_ACL)


async def _sources_with_chunks(session: AsyncSession, source_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
    if not source_ids:
        return set()
    found = await session.scalars(
        select(Chunk.sourceId).where(Chunk.sourceId.in_(list(source_ids))).distinct()
    )
    return set(found)
