from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import InvalidInput
from app.models import Chunk, Claim, Craft, Source
from app.research.embedding import TextEmbedder, checked_vectors
from app.research.planning import MODE_POLICIES
from app.research.retrieval import ChunkHit, ClaimHit, KnowledgeHits, KnowledgeQuery

from .fusion import FusedItem, reciprocal_rank_fusion
from .statements import (
    EVERY_CRAFT,
    CraftScope,
    chunk_conditions,
    chunk_lexical_ranking,
    chunk_vector_ranking,
    claim_conditions,
    claim_lexical_ranking,
    claim_vector_ranking,
)
from .text import or_tsquery, query_text

__all__ = ["CORPUS_TIER", "SessionScopedSearch", "StoredKnowledgeSearch", "craft_scope"]

CORPUS_TIER = "T2"
SCORE_DIGITS = 9


class SessionScopedSearch:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], *, embed: TextEmbedder) -> None:
        self._sessions = sessions
        self._embed = embed

    async def search(self, query: KnowledgeQuery) -> KnowledgeHits:
        async with self._sessions() as session:
            return await StoredKnowledgeSearch(session, embed=self._embed).search(query)


class StoredKnowledgeSearch:
    def __init__(self, session: AsyncSession, *, embed: TextEmbedder) -> None:
        self._session = session
        self._embed = embed

    async def search(self, query: KnowledgeQuery) -> KnowledgeHits:
        (vector,) = checked_vectors(await self._embed([query_text(query.text)]), expected=1)
        scope = await craft_scope(self._session, query.craft_slug)
        tsquery = or_tsquery(query.text)
        conditions = claim_conditions(scope, mode=query.mode, facets=query.facets)
        claims = await self._fuse(
            claim_lexical_ranking(conditions, tsquery) if tsquery else None,
            claim_vector_ranking(conditions, vector),
            limit=query.limit,
        )
        chunks: list[FusedItem[uuid.UUID]] = []
        if CORPUS_TIER in MODE_POLICIES[query.mode].tiers:
            conditions = chunk_conditions(scope, mode=query.mode, facets=query.facets, acls=query.chunk_acls)
            chunks = await self._fuse(
                chunk_lexical_ranking(conditions, tsquery) if tsquery else None,
                chunk_vector_ranking(conditions, vector),
                limit=query.limit,
            )
        return KnowledgeHits(
            craft_slug=query.craft_slug,
            claims=tuple(await self._claim_hits(claims)),
            chunks=tuple(await self._chunk_hits(chunks)),
        )

    async def _fuse(
        self, lexical: Select[tuple[uuid.UUID]] | None, vector: Select[tuple[uuid.UUID]], *, limit: int
    ) -> list[FusedItem[uuid.UUID]]:
        lexical_ids = list((await self._session.scalars(lexical)).all()) if lexical is not None else []
        vector_ids = list((await self._session.scalars(vector)).all())
        return reciprocal_rank_fusion([lexical_ids, vector_ids])[:limit]

    async def _claim_hits(self, fused: Sequence[FusedItem[uuid.UUID]]) -> list[ClaimHit]:
        if not fused:
            return []
        columns = (Claim.id, Claim.text, Claim.evidenceLevel, Claim.subjectType, Claim.subjectId)
        rows = await self._session.execute(select(*columns).where(Claim.id.in_([item.key for item in fused])))
        by_id = {row.id: row for row in rows}
        return [
            ClaimHit(
                claim_id=item.key,
                text=by_id[item.key].text,
                level=by_id[item.key].evidenceLevel,
                subject_type=by_id[item.key].subjectType,
                subject_id=by_id[item.key].subjectId,
                **_ranking_fields(item),
            )
            for item in fused
        ]

    async def _chunk_hits(self, fused: Sequence[FusedItem[uuid.UUID]]) -> list[ChunkHit]:
        if not fused:
            return []
        columns = (
            Chunk.id,
            Chunk.sourceId,
            Chunk.ordinal,
            Chunk.locator,
            Chunk.text,
            Source.kind,
            Source.title,
        )
        rows = await self._session.execute(
            select(*columns)
            .join(Source, Source.id == Chunk.sourceId)
            .where(Chunk.id.in_([item.key for item in fused]))
        )
        by_id = {row.id: row for row in rows}
        return [
            ChunkHit(
                chunk_id=item.key,
                source_id=by_id[item.key].sourceId,
                ordinal=by_id[item.key].ordinal,
                locator=by_id[item.key].locator,
                text=by_id[item.key].text,
                source_kind=by_id[item.key].kind,
                source_title=by_id[item.key].title,
                **_ranking_fields(item),
            )
            for item in fused
        ]


async def craft_scope(session: AsyncSession, slug: str | None) -> CraftScope:
    if slug is None:
        return EVERY_CRAFT
    row = (await session.execute(select(Craft.id, Craft.subCategoryId).where(Craft.slug == slug))).first()
    if row is None:
        raise InvalidInput(f"No craft has the slug {slug!r}")
    return CraftScope(craft_id=row.id, sub_category_id=row.subCategoryId)


def _ranking_fields(item: FusedItem[uuid.UUID]) -> dict[str, float | int | None]:
    lexical_rank, vector_rank = item.ranks
    return {
        "score": round(item.score, SCORE_DIGITS),
        "lexical_rank": lexical_rank,
        "vector_rank": vector_rank,
    }
