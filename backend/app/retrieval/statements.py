from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, exists, func, or_, select

from app.models import Chunk, Claim, ClaimSource, Concept, ConceptEdge, Source
from app.research.retrieval import (
    MODE_CLAIM_LEVELS,
    MODE_CLAIM_STATUSES,
    RESTRICTED_SENSITIVITY,
    VISIBLE_SENSITIVITY,
)

__all__ = [
    "EVERY_CRAFT",
    "RANKING_DEPTH",
    "TEXT_SEARCH_CONFIG",
    "CraftScope",
    "chunk_conditions",
    "chunk_lexical_ranking",
    "chunk_vector_ranking",
    "claim_conditions",
    "claim_lexical_ranking",
    "claim_vector_ranking",
    "lexical_rank",
    "readable_citations",
    "scope_claims",
    "scope_concepts",
    "text_query",
]

RANKING_DEPTH = 30
TEXT_SEARCH_CONFIG = "english"


@dataclass(frozen=True)
class CraftScope:
    craft_id: uuid.UUID | None
    sub_category_id: uuid.UUID | None


EVERY_CRAFT = CraftScope(craft_id=None, sub_category_id=None)


def scope_concepts(scope: CraftScope, *, facets: Sequence[str] = ()) -> Select[tuple[uuid.UUID]]:
    visible = Concept.sensitivity == VISIBLE_SENSITIVITY
    owned = [or_(*_owners(scope))] if scope.craft_id is not None else []
    statement = select(Concept.id).where(*owned, visible)
    if facets:
        statement = statement.where(Concept.type.in_(list(facets)))
    return statement


def _owners(scope: CraftScope) -> list[ColumnElement[bool]]:
    owners: list[ColumnElement[bool]] = [Concept.craftId == scope.craft_id]
    if scope.sub_category_id is not None:
        owners.append(and_(Concept.craftId.is_(None), Concept.subCategoryId == scope.sub_category_id))
    return owners


def scope_claims(scope: CraftScope, *, facets: Sequence[str] = ()) -> ColumnElement[bool]:
    concepts = scope_concepts(scope, facets=facets)
    edges = select(ConceptEdge.id).where(
        or_(ConceptEdge.srcId.in_(concepts), ConceptEdge.dstId.in_(concepts))
    )
    return or_(
        and_(Claim.subjectType == "CONCEPT", Claim.subjectId.in_(concepts)),
        and_(Claim.subjectType == "EDGE", Claim.subjectId.in_(edges)),
    )


def claim_conditions(
    scope: CraftScope, *, mode: str, facets: Sequence[str] = ()
) -> list[ColumnElement[bool]]:
    cited = exists().where(
        ClaimSource.claimId == Claim.id,
        ClaimSource.sourceId == Source.id,
        Source.sensitivity != RESTRICTED_SENSITIVITY,
    )
    return [
        scope_claims(scope, facets=facets),
        Claim.status.in_(MODE_CLAIM_STATUSES[mode]),
        Claim.evidenceLevel.in_(MODE_CLAIM_LEVELS[mode]),
        Claim.sensitivity == VISIBLE_SENSITIVITY,
        cited,
    ]


def readable_citations(claim_ids: Sequence[uuid.UUID], *, acls: Sequence[str]) -> Select[tuple[ClaimSource]]:
    readable = or_(
        ClaimSource.chunkId.is_(None),
        and_(Chunk.acl.in_(list(acls)), Chunk.sensitivity != RESTRICTED_SENSITIVITY),
    )
    return (
        select(ClaimSource)
        .outerjoin(Chunk, Chunk.id == ClaimSource.chunkId)
        .where(ClaimSource.claimId.in_(list(claim_ids)), readable)
    )


def chunk_conditions(
    scope: CraftScope, *, mode: str, facets: Sequence[str] = (), acls: Sequence[str]
) -> list[ColumnElement[bool]]:
    claims = select(Claim.id).where(*claim_conditions(scope, mode=mode, facets=facets))
    sources = select(Source.id).where(
        Source.id.in_(select(ClaimSource.sourceId).where(ClaimSource.claimId.in_(claims))),
        Source.sensitivity != RESTRICTED_SENSITIVITY,
    )
    return [
        Chunk.sourceId.in_(sources),
        Chunk.acl.in_(list(acls)),
        Chunk.sensitivity != RESTRICTED_SENSITIVITY,
    ]


def claim_lexical_ranking(
    conditions: Sequence[ColumnElement[bool]], tsquery: str, *, depth: int = RANKING_DEPTH
) -> Select[tuple[uuid.UUID]]:
    return _lexical(Claim.id, Claim.tsv, conditions, tsquery, depth)


def chunk_lexical_ranking(
    conditions: Sequence[ColumnElement[bool]], tsquery: str, *, depth: int = RANKING_DEPTH
) -> Select[tuple[uuid.UUID]]:
    return _lexical(Chunk.id, Chunk.tsv, conditions, tsquery, depth)


def claim_vector_ranking(
    conditions: Sequence[ColumnElement[bool]], vector: Sequence[float], *, depth: int = RANKING_DEPTH
) -> Select[tuple[uuid.UUID]]:
    return _vector(Claim.id, Claim.embedding, conditions, vector, depth)


def chunk_vector_ranking(
    conditions: Sequence[ColumnElement[bool]], vector: Sequence[float], *, depth: int = RANKING_DEPTH
) -> Select[tuple[uuid.UUID]]:
    return _vector(Chunk.id, Chunk.embedding, conditions, vector, depth)


def text_query(tsquery: str) -> ColumnElement[Any]:
    return func.to_tsquery(TEXT_SEARCH_CONFIG, tsquery)


def lexical_rank(tsv: Any, query: ColumnElement[Any]) -> ColumnElement[float]:
    return func.ts_rank_cd(tsv, query)


def _lexical(
    key: ColumnElement[uuid.UUID],
    tsv: Any,
    conditions: Sequence[ColumnElement[bool]],
    tsquery: str,
    depth: int,
) -> Select[tuple[uuid.UUID]]:
    query = text_query(tsquery)
    rank = lexical_rank(tsv, query)
    return select(key).where(*conditions, tsv.op("@@")(query)).order_by(rank.desc(), key).limit(depth)


def _vector(
    key: ColumnElement[uuid.UUID],
    embedding: Any,
    conditions: Sequence[ColumnElement[bool]],
    vector: Sequence[float],
    depth: int,
) -> Select[tuple[uuid.UUID]]:
    distance = embedding.cosine_distance(list(vector))
    scoped = (
        select(key.label("id"), distance.label("distance"))
        .where(*conditions, embedding.is_not(None))
        .cte("scoped")
        .prefix_with("MATERIALIZED")
    )
    return select(scoped.c.id).order_by(scoped.c.distance, scoped.c.id).limit(depth)
