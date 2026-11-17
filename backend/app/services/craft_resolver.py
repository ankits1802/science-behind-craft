from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Sequence
from itertools import batched

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import release_connection
from app.data.craft_master_loader import ACTIVE
from app.models import AdminDistrict, AdminState, Craft, CraftAlias, CraftLocation, CraftSpelling
from app.research.crafts import CraftQuery, CraftResolution
from app.research.embedding import TextEmbedder, checked_vectors
from app.services.craft_index import AliasRecord, CraftIndex, CraftRecord, SpellingRecord, build_index
from app.services.craft_matching import (
    SEMANTIC_TOP_K,
    SemanticHit,
    lexical_match,
    resolution_from,
    slug_resolution,
)

__all__ = [
    "DESCRIPTOR_BATCH",
    "INDEX_TTL_SECONDS",
    "CraftIndexStore",
    "DatabaseCraftResolver",
    "descriptor_text",
    "fill_descriptor_embeddings",
    "load_index",
]

INDEX_TTL_SECONDS = 300.0
DESCRIPTOR_BATCH = 50
DESCRIPTOR_SEPARATOR = "; "


class CraftIndexStore:
    def __init__(
        self, *, ttl_seconds: float = INDEX_TTL_SECONDS, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._index: CraftIndex | None = None
        self._loaded_at = 0.0

    async def get(self, session: AsyncSession) -> CraftIndex:
        now = self._clock()
        if self._index is None or now - self._loaded_at >= self._ttl:
            self._index = await load_index(session)
            self._loaded_at = now
        return self._index

    def invalidate(self) -> None:
        self._index = None


class DatabaseCraftResolver:
    def __init__(self, session: AsyncSession, *, store: CraftIndexStore, embed: TextEmbedder) -> None:
        self._session = session
        self._store = store
        self._embed = embed

    async def resolve(self, query: CraftQuery) -> CraftResolution:
        index = await self._store.get(self._session)
        if query.craft_slug:
            return slug_resolution(index, query.craft_slug, query.text)
        match = lexical_match(index, query.text)
        lexical = resolution_from(index, match)
        if lexical.status == "RESOLVED" or not index.embedded:
            return lexical
        return resolution_from(index, match, await self._semantic(query.text))

    async def _semantic(self, text: str) -> list[SemanticHit]:
        await release_connection(self._session)
        (vector,) = checked_vectors(await self._embed([text]), expected=1)
        distance = Craft.descriptorEmbedding.cosine_distance(vector)
        rows = (
            await self._session.execute(
                select(Craft.id, distance.label("distance"))
                .where(
                    Craft.status == ACTIVE,
                    Craft.isCatchAll.is_(False),
                    Craft.descriptorEmbedding.is_not(None),
                )
                .order_by(distance, Craft.slug)
                .limit(SEMANTIC_TOP_K)
            )
        ).all()
        return [SemanticHit(craft_id, 1.0 - float(gap)) for craft_id, gap in rows]


def descriptor_text(name: str, names: Sequence[str]) -> str:
    seen: dict[str, str] = {}
    for value in (name, *names):
        label = (value or "").strip()
        if label and label.casefold() not in seen:
            seen[label.casefold()] = label
    return DESCRIPTOR_SEPARATOR.join(seen.values())


async def fill_descriptor_embeddings(
    session: AsyncSession, embed: TextEmbedder, *, batch_size: int = DESCRIPTOR_BATCH
) -> int:
    crafts = (
        await session.execute(
            select(Craft.id, Craft.name, Craft.localName)
            .where(Craft.status == ACTIVE, Craft.isCatchAll.is_(False), Craft.descriptorEmbedding.is_(None))
            .order_by(Craft.slug)
        )
    ).all()
    names = await _alias_names(session, [craft_id for craft_id, _, _ in crafts])
    filled = 0
    for chunk in batched(crafts, batch_size, strict=False):
        texts = [descriptor_text(name, [local or "", *names.get(cid, [])]) for cid, name, local in chunk]
        vectors = checked_vectors(await embed(texts), expected=len(texts))
        for (craft_id, _, _), vector in zip(chunk, vectors, strict=True):
            await session.execute(
                update(Craft).where(Craft.id == craft_id).values(descriptorEmbedding=vector)
            )
        await session.commit()
        filled += len(chunk)
    return filled


async def load_index(session: AsyncSession) -> CraftIndex:
    places = await _craft_places(session)
    crafts = [
        CraftRecord(
            id=row.id,
            slug=row.slug,
            name=row.name,
            status=row.status,
            is_catch_all=row.isCatchAll,
            merged_into=row.mergedIntoId,
            craft_code=row.craftCode,
            local_name=row.localName,
            places=(*row.stateOfPractice, *row.stateOfOrigin, *places.get(row.id, ())),
        )
        for row in (await session.execute(select(*_CRAFT_COLUMNS))).all()
    ]
    aliases = [
        AliasRecord(craft_id, alias)
        for craft_id, alias in (
            await session.execute(
                select(CraftAlias.craftId, CraftAlias.alias).where(CraftAlias.status == ACTIVE)
            )
        ).all()
    ]
    spellings = [
        SpellingRecord(code, label)
        for code, label in (await session.execute(select(CraftSpelling.craftCode, CraftSpelling.label))).all()
    ]
    embedded = await session.scalar(
        select(func.count(Craft.id)).where(Craft.status == ACTIVE, Craft.descriptorEmbedding.is_not(None))
    )
    return build_index(crafts, aliases, spellings, embedded=int(embedded or 0))


_CRAFT_COLUMNS = (
    Craft.id,
    Craft.slug,
    Craft.name,
    Craft.localName,
    Craft.status,
    Craft.isCatchAll,
    Craft.mergedIntoId,
    Craft.craftCode,
    Craft.stateOfPractice,
    Craft.stateOfOrigin,
)


async def _craft_places(session: AsyncSession) -> dict[uuid.UUID, list[str]]:
    rows = (
        await session.execute(
            select(CraftLocation.craftId, CraftLocation.placeLabel, AdminDistrict.name, AdminState.name)
            .outerjoin(AdminDistrict, AdminDistrict.lgd == CraftLocation.districtLgd)
            .outerjoin(AdminState, AdminState.lgd == CraftLocation.stateLgd)
        )
    ).all()
    found: dict[uuid.UUID, list[str]] = {}
    for craft_id, *labels in rows:
        found.setdefault(craft_id, []).extend(label for label in labels if label)
    return found


async def _alias_names(session: AsyncSession, craft_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    if not craft_ids:
        return {}
    rows = (
        await session.execute(
            select(CraftAlias.craftId, CraftAlias.alias)
            .where(CraftAlias.craftId.in_(craft_ids), CraftAlias.status == ACTIVE)
            .order_by(CraftAlias.craftId, CraftAlias.alias)
        )
    ).all()
    found: dict[uuid.UUID, list[str]] = {}
    for craft_id, alias in rows:
        found.setdefault(craft_id, []).append(alias)
    return found
