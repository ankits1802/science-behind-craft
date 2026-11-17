from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.core.shielded import ShieldedWork
from app.data.craft_master_loader import ID_NAMESPACE
from app.models import KnowledgePiece as PieceRow
from app.models.enums import EXPLAINER_DEPTHS
from app.research.blocks import ProcessLadderBlock
from app.research.depth import depth_at_least
from app.research.embedding import TextEmbedder, checked_vectors
from app.research.explainer import Block
from app.research.knowledge_pieces import KnowledgePiece, PieceSlot, ReuseAsk, knowledge_piece
from app.research.piece_reuse import reusable_groups
from app.research.piece_topics import facet_topics
from app.retrieval.indexing import embed_pieces
from app.retrieval.text import query_text
from app.science.ladder import ladder_problems
from app.science.records import ProcessRecords

from . import knowledge_view
from .craft_process import process_records
from .piece_lookup import (
    PieceAsk,
    PieceLookup,
    ReusedSection,
    candidate_pieces,
    claim_states,
    topic_subjects,
)

__all__ = ["BuiltSection", "PieceStore", "SqlPieceStore", "piece_id", "storable"]

logger = logging.getLogger(__name__)

NO_DISTANCE = 2.0


@dataclass(frozen=True)
class BuiltSection:
    facet: str
    blocks: tuple[Block, ...]


class PieceStore(Protocol):
    async def reusable(self, ask: PieceAsk) -> PieceLookup: ...

    async def keep(
        self, lookup: PieceLookup, *, answer_id: uuid.UUID, depth: str, sections: Sequence[BuiltSection]
    ) -> None: ...


def piece_id(answer_id: uuid.UUID, block_id: str) -> uuid.UUID:
    return uuid.uuid5(ID_NAMESPACE, f"knowledge-piece:{answer_id}:{block_id}")


def storable(block: Block) -> bool:
    return bool(block.cited_claim_ids()) and bool(block.cited_source_ids())


class SqlPieceStore:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], *, embed: TextEmbedder, shield: ShieldedWork
    ) -> None:
        self._sessions = sessions
        self._embed = embed
        self._shield = shield

    async def reusable(self, ask: PieceAsk) -> PieceLookup:
        if ask.craft is None:
            return PieceLookup()
        async with self._sessions() as session:
            craft = await knowledge_view.resolve_craft(session, ask.craft.slug)
            if craft is None:
                return PieceLookup()
            topics = facet_topics(ask.facets, await topic_subjects(session, craft, ask.question))
            if ask.fresh or not topics:
                return PieceLookup(craft_id=craft.id, topics=topics)
            pieces = await candidate_pieces(session, craft.id, topics)
            states, cited = await claim_states(session, pieces)
            ladders = any(isinstance(piece.payload, ProcessLadderBlock) for piece in pieces)
            records = await process_records(session, craft) if ladders else None
        reused: dict[str, ReusedSection] = {}
        for facet, topic in topics.items():
            reuse = ReuseAsk(craft_id=craft.id, facet=facet, topic_key=topic, depth=ask.depth)
            groups = [
                group for group in reusable_groups(pieces, reuse, states) if _ladders_hold(group, records)
            ]
            if groups:
                reused[facet] = ReusedSection(pieces=await self._closest(groups, ask.question), cited=cited)
        return PieceLookup(craft_id=craft.id, topics=topics, reused=reused)

    async def keep(
        self, lookup: PieceLookup, *, answer_id: uuid.UUID, depth: str, sections: Sequence[BuiltSection]
    ) -> None:
        pieces = _pieces(lookup, answer_id=answer_id, depth=depth, sections=sections)
        if pieces:
            await self._shield.run(self._kept(pieces), name="knowledge pieces")

    async def _closest(
        self, groups: Sequence[tuple[KnowledgePiece, ...]], question: str
    ) -> tuple[KnowledgePiece, ...]:
        if len(groups) == 1:
            return groups[0]
        vector = checked_vectors(await self._embed([query_text(question)]), expected=1)[0]
        ids = [piece.id for group in groups for piece in group]
        async with self._sessions() as session:
            rows = await session.execute(
                select(PieceRow.id, PieceRow.embedding.cosine_distance(vector)).where(PieceRow.id.in_(ids))
            )
            distances = {row[0]: row[1] for row in rows if row[1] is not None}
        return min(groups, key=lambda group: min(distances.get(piece.id, NO_DISTANCE) for piece in group))

    async def _kept(self, pieces: Sequence[KnowledgePiece]) -> None:
        async with self._sessions() as session:
            for piece in pieces:
                await _insert(session, piece)
                await _supersede(session, piece)
            await session.commit()
            try:
                await embed_pieces(session, self._embed, piece_ids=[piece.id for piece in pieces])
            except AppError:
                logger.warning(
                    "knowledge pieces kept without vectors; embed_knowledge fills them", exc_info=True
                )


def _ladders_hold(group: Sequence[KnowledgePiece], records: ProcessRecords | None) -> bool:
    ladders = [piece.payload for piece in group if isinstance(piece.payload, ProcessLadderBlock)]
    if ladders and records is None:
        return False
    problems = [problem for ladder in ladders for problem in ladder_problems(ladder, records)]
    if problems:
        logger.info("a stored ladder no longer matches the process rows: %s", "; ".join(problems))
    return not problems


def _pieces(
    lookup: PieceLookup, *, answer_id: uuid.UUID, depth: str, sections: Sequence[BuiltSection]
) -> list[KnowledgePiece]:
    created_at = datetime.now(UTC)
    return [
        knowledge_piece(
            block,
            PieceSlot(lookup.craft_id, section.facet, lookup.topics[section.facet], depth),
            piece_id=piece_id(answer_id, block.id),
            answer_id=answer_id,
            created_at=created_at,
        )
        for section in sections
        if lookup.craft_id is not None and section.facet in lookup.topics
        for block in section.blocks
        if storable(block)
    ]


async def _insert(session: AsyncSession, piece: KnowledgePiece) -> None:
    await session.execute(
        insert(PieceRow)
        .values(
            id=piece.id,
            craftId=piece.craft_id,
            kind=piece.kind,
            facet=piece.facet,
            topicKey=piece.topic_key,
            language=piece.language,
            depth=piece.depth,
            payload=piece.payload.model_dump(mode="json", by_alias=True),
            claimIds=piece.claim_ids,
            sourceIds=piece.source_ids,
            contentHash=piece.content_hash,
            createdFromAnswerId=piece.created_from_answer_id,
            createdAt=piece.created_at,
        )
        .on_conflict_do_nothing()
    )


async def _supersede(session: AsyncSession, piece: KnowledgePiece) -> None:
    shallower = [depth for depth in EXPLAINER_DEPTHS if depth_at_least(piece.depth, depth)]
    await session.execute(
        update(PieceRow)
        .where(
            PieceRow.craftId == piece.craft_id,
            PieceRow.facet == piece.facet,
            PieceRow.topicKey == piece.topic_key,
            PieceRow.kind == piece.kind,
            PieceRow.depth.in_(shallower),
            PieceRow.id != piece.id,
            PieceRow.supersededById.is_(None),
            PieceRow.createdAt <= piece.created_at,
        )
        .values(supersededById=piece.id)
    )
