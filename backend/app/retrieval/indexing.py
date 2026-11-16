from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from itertools import batched

from sqlalchemy import ColumnElement, Select, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import Chunk, Claim, Source
from app.research.embedding import TextEmbedder, checked_vectors
from app.research.retrieval import HIDDEN_CLAIM_STATUSES, RESTRICTED_SENSITIVITY, VISIBLE_SENSITIVITY

from .chunking import TextChunk, chunk_text
from .text import document_text

__all__ = ["EMBED_BATCH", "EmbeddedCounts", "embed_pending", "embed_written", "replace_source_chunks"]

EMBED_BATCH = 50
DEFAULT_CHUNK_ACL = "PUBLIC"


@dataclass(frozen=True)
class EmbeddedCounts:
    claims: int
    chunks: int


@dataclass(frozen=True)
class _Pending:
    id: uuid.UUID
    text: str


async def replace_source_chunks(
    session: AsyncSession, source_id: uuid.UUID, text: str, *, lang: str = "en", acl: str = DEFAULT_CHUNK_ACL
) -> int:
    source = await session.get(Source, source_id)
    if source is None:
        raise InvalidInput(f"No source has the id {source_id}")
    pieces = chunk_text(text)
    stored = {
        chunk.ordinal: chunk
        for chunk in (await session.scalars(select(Chunk).where(Chunk.sourceId == source_id))).all()
    }
    for piece in pieces:
        _apply(session, stored.get(piece.ordinal), piece, source=source, lang=lang, acl=acl)
    await session.execute(delete(Chunk).where(Chunk.sourceId == source_id, Chunk.ordinal >= len(pieces)))
    await session.flush()
    return len(pieces)


async def embed_pending(
    session: AsyncSession, embed: TextEmbedder, *, batch_size: int = EMBED_BATCH
) -> EmbeddedCounts:
    return await _embed(session, embed, claim_scope=None, chunk_scope=None, batch_size=batch_size)


async def embed_written(
    session: AsyncSession,
    embed: TextEmbedder,
    *,
    claim_ids: Collection[uuid.UUID],
    source_ids: Collection[uuid.UUID],
    batch_size: int = EMBED_BATCH,
) -> EmbeddedCounts:
    return await _embed(
        session,
        embed,
        claim_scope=Claim.id.in_(list(claim_ids)),
        chunk_scope=Chunk.sourceId.in_(list(source_ids)),
        batch_size=batch_size,
    )


async def _embed(
    session: AsyncSession,
    embed: TextEmbedder,
    *,
    claim_scope: ColumnElement[bool] | None,
    chunk_scope: ColumnElement[bool] | None,
    batch_size: int,
) -> EmbeddedCounts:
    if batch_size < 1:
        raise InvalidInput(f"An embedding batch holds at least one text, not {batch_size}")
    claims = await _pending_claims(session, claim_scope)
    await _fill(session, embed, Claim, claims, batch_size=batch_size)
    chunks = await _pending_chunks(session, chunk_scope)
    await _fill(session, embed, Chunk, chunks, batch_size=batch_size)
    return EmbeddedCounts(claims=len(claims), chunks=len(chunks))


def _apply(
    session: AsyncSession, chunk: Chunk | None, piece: TextChunk, *, source: Source, lang: str, acl: str
) -> None:
    if chunk is None:
        session.add(
            Chunk(
                sourceId=source.id,
                ordinal=piece.ordinal,
                locator=piece.locator,
                text=piece.text,
                lang=lang,
                acl=acl,
                sensitivity=source.sensitivity,
            )
        )
        return
    if chunk.text != piece.text:
        chunk.text = piece.text
        chunk.embedding = None
    chunk.locator = piece.locator
    chunk.lang = lang
    chunk.acl = acl
    chunk.sensitivity = source.sensitivity


async def _pending_claims(session: AsyncSession, scope: ColumnElement[bool] | None) -> list[_Pending]:
    statement = select(Claim.id, Claim.text).where(
        Claim.embedding.is_(None),
        Claim.sensitivity == VISIBLE_SENSITIVITY,
        Claim.status.not_in(HIDDEN_CLAIM_STATUSES),
    )
    rows = await session.execute(_scoped(statement, scope).order_by(Claim.id))
    return [_Pending(row.id, document_text(row.text)) for row in rows]


async def _pending_chunks(session: AsyncSession, scope: ColumnElement[bool] | None) -> list[_Pending]:
    statement = (
        select(Chunk.id, Chunk.text, Source.title)
        .join(Source, Source.id == Chunk.sourceId)
        .where(
            Chunk.embedding.is_(None),
            Chunk.sensitivity != RESTRICTED_SENSITIVITY,
            Source.sensitivity != RESTRICTED_SENSITIVITY,
        )
    )
    rows = await session.execute(_scoped(statement, scope).order_by(Chunk.id))
    return [_Pending(row.id, document_text(row.text, title=row.title)) for row in rows]


def _scoped[T: tuple[object, ...]](statement: Select[T], scope: ColumnElement[bool] | None) -> Select[T]:
    return statement if scope is None else statement.where(scope)


async def _fill(
    session: AsyncSession,
    embed: TextEmbedder,
    model: type[Claim] | type[Chunk],
    pending: Sequence[_Pending],
    *,
    batch_size: int,
) -> None:
    for group in batched(pending, batch_size, strict=False):
        texts = [item.text for item in group]
        vectors = checked_vectors(await embed(texts), expected=len(texts))
        for item, vector in zip(group, vectors, strict=True):
            await session.execute(update(model).where(model.id == item.id).values(embedding=vector))
        await session.commit()
