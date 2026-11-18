import uuid
from collections.abc import Iterable

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, ClaimSource, Source
from app.research.retrieval import PUBLIC_CHUNK_ACL, RESEARCHER_CHUNK_ACL, RESTRICTED_SENSITIVITY
from app.retrieval.indexing import replace_source_chunks

__all__ = [
    "CLOSED_QUOTE",
    "OPEN_SOURCE",
    "RESTRICTED_CHUNK_QUOTE",
    "RESTRICTED_SOURCE_QUOTE",
    "quote_closed",
    "quote_restricted",
    "store_closed_sources",
]

CLOSED_QUOTE = "Alum fixes the madder red, a closed monograph says."
RESTRICTED_CHUNK_QUOTE = "Alum is weighed out by the dyer's own secret measure."
RESTRICTED_SOURCE_QUOTE = "Alum came by camel from the salt flats, a restricted letter says."


def key(name: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"test-closed-quotes/{name}")


CLOSED_SOURCE = key("closed-monograph")
GUARDED_SOURCE = key("guarded-notebook")
RESTRICTED_SOURCE = key("restricted-letter")
OPEN_SOURCE = key("open-paper")


async def store_closed_sources(session: AsyncSession) -> None:
    session.add_all(
        [
            Source(id=CLOSED_SOURCE, kind="PAPER", title="A closed monograph on alum"),
            Source(id=GUARDED_SOURCE, kind="PAPER", title="A field notebook on alum"),
            Source(
                id=RESTRICTED_SOURCE,
                kind="PAPER",
                title="A restricted letter on alum",
                sensitivity=RESTRICTED_SENSITIVITY,
            ),
            Source(id=OPEN_SOURCE, kind="PAPER", title="An open paper on alum"),
        ]
    )
    await session.flush()
    await replace_source_chunks(session, CLOSED_SOURCE, CLOSED_QUOTE, acl=RESEARCHER_CHUNK_ACL)
    await replace_source_chunks(session, GUARDED_SOURCE, RESTRICTED_CHUNK_QUOTE, acl=PUBLIC_CHUNK_ACL)
    await session.execute(
        update(Chunk).where(Chunk.sourceId == GUARDED_SOURCE).values(sensitivity=RESTRICTED_SENSITIVITY)
    )
    await session.flush()


async def quote_closed(session: AsyncSession, claim_ids: Iterable[uuid.UUID]) -> None:
    chunk = await _chunk_of(session, CLOSED_SOURCE)
    session.add_all(
        ClaimSource(
            claimId=claim_id,
            sourceId=CLOSED_SOURCE,
            chunkId=chunk,
            quote=CLOSED_QUOTE,
            quoteCheck="PASS",
        )
        for claim_id in dict.fromkeys(claim_ids)
    )
    await session.flush()


async def quote_restricted(session: AsyncSession, claim_id: uuid.UUID) -> None:
    chunk = await _chunk_of(session, GUARDED_SOURCE)
    session.add_all(
        [
            ClaimSource(
                claimId=claim_id,
                sourceId=GUARDED_SOURCE,
                chunkId=chunk,
                quote=RESTRICTED_CHUNK_QUOTE,
                quoteCheck="PASS",
            ),
            ClaimSource(claimId=claim_id, sourceId=RESTRICTED_SOURCE, quote=RESTRICTED_SOURCE_QUOTE),
        ]
    )
    await session.flush()


async def _chunk_of(session: AsyncSession, source_id: uuid.UUID) -> uuid.UUID:
    return (await session.execute(select(Chunk.id).where(Chunk.sourceId == source_id))).scalar_one()
