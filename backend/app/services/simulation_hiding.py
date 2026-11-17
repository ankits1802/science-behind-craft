from __future__ import annotations

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import Answer, KnowledgePiece as PieceRow, User
from app.research.blocks_play import SimulationBlock
from app.research.explainer import Explainer, explainer_blocks
from app.research.knowledge_pieces import concept_slot, knowledge_piece, piece_content_hash
from app.research.piece_reuse import SIMULATION_KIND

from . import audit
from .explainer_payload import stored_explainer
from .piece_store import piece_id, piece_values, storable

__all__ = [
    "SIMULATION_HIDDEN_ACTION",
    "SIMULATION_SHOWN_ACTION",
    "HiddenPiece",
    "SimulationHide",
    "hidden_marked",
    "set_simulation_hidden",
    "simulation_piece_id",
    "with_hidden_marks",
]

SIMULATION_HIDDEN_ACTION = "explainers.simulation_hidden"
SIMULATION_SHOWN_ACTION = "explainers.simulation_shown"
PIECE_TARGET = "KnowledgePiece"


@dataclass(frozen=True)
class SimulationHide:
    answer_id: uuid.UUID
    block_id: str
    hidden: bool


@dataclass(frozen=True)
class HiddenPiece:
    piece_id: uuid.UUID
    hidden: bool


async def set_simulation_hidden(
    session: AsyncSession, change: SimulationHide, *, user: User, now: datetime
) -> HiddenPiece | None:
    payload = await session.scalar(
        select(Answer.payload).where(Answer.id == change.answer_id, Answer.userId == user.id)
    )
    explainer = stored_explainer(change.answer_id, payload)
    found = _simulation(explainer, change.block_id) if explainer is not None else None
    if explainer is None or found is None:
        return None
    row = await _kept_row(session, explainer, *found, now=now)
    if row is None:
        return None
    if _marked(row, user, hidden=change.hidden, now=now):
        await audit.record(
            session,
            action=SIMULATION_HIDDEN_ACTION if change.hidden else SIMULATION_SHOWN_ACTION,
            actor=user,
            target_type=PIECE_TARGET,
            target_id=row.id,
            detail={"answerId": str(change.answer_id), "blockId": change.block_id},
        )
    await session.commit()
    return HiddenPiece(row.id, change.hidden)


def simulation_piece_id(answer_id: uuid.UUID, block: SimulationBlock) -> uuid.UUID:
    return block.reuse.piece_id if block.reuse is not None else piece_id(answer_id, block.id)


async def with_hidden_marks(session: AsyncSession, explainer: Explainer) -> Explainer:
    blocks = [block for block in explainer_blocks(explainer) if isinstance(block, SimulationBlock)]
    if not blocks:
        return explainer
    ids = {block.id: simulation_piece_id(explainer.answer_id, block) for block in blocks}
    hashes = {block.id: piece_content_hash(block) for block in blocks}
    rows = (
        await session.execute(
            select(PieceRow.id, PieceRow.contentHash).where(
                PieceRow.kind == SIMULATION_KIND,
                PieceRow.hiddenAt.is_not(None),
                or_(
                    PieceRow.id.in_(sorted(set(ids.values()))),
                    PieceRow.contentHash.in_(sorted(set(hashes.values()))),
                ),
            )
        )
    ).all()
    hidden_ids = {row[0] for row in rows}
    hidden_hashes = {row[1] for row in rows}
    marked = {
        block.id for block in blocks if ids[block.id] in hidden_ids or hashes[block.id] in hidden_hashes
    }
    return hidden_marked(explainer, marked)


def hidden_marked(explainer: Explainer, block_ids: Collection[str]) -> Explainer:
    sections = [
        section.model_copy(
            update={
                "blocks": [
                    block.model_copy(update={"hidden": True})
                    if isinstance(block, SimulationBlock) and block.id in block_ids
                    else block
                    for block in section.blocks
                ]
            }
        )
        for section in explainer.sections
    ]
    return explainer.model_copy(update={"sections": sections})


async def _kept_row(
    session: AsyncSession, explainer: Explainer, block: SimulationBlock, facet: str, *, now: datetime
) -> PieceRow | None:
    own = simulation_piece_id(explainer.answer_id, block)
    row = await _locked(session, PieceRow.id == own)
    if row is None:
        row = await _locked(session, PieceRow.contentHash == piece_content_hash(block))
    if row is not None or not storable(block):
        return row
    try:
        slot = concept_slot(block, facet, explainer.understood.depth)
    except InvalidInput:
        return None
    kept = knowledge_piece(
        block,
        slot,
        piece_id=piece_id(explainer.answer_id, block.id),
        answer_id=explainer.answer_id,
        created_at=now,
    )
    await session.execute(insert(PieceRow).values(piece_values(kept)).on_conflict_do_nothing())
    return await _locked(session, PieceRow.id == kept.id)


async def _locked(session: AsyncSession, *where: ColumnElement[bool]) -> PieceRow | None:
    return await session.scalar(
        select(PieceRow)
        .where(PieceRow.kind == SIMULATION_KIND, *where)
        .order_by(PieceRow.createdAt)
        .limit(1)
        .with_for_update()
    )


def _simulation(explainer: Explainer, block_id: str) -> tuple[SimulationBlock, str] | None:
    for section in explainer.sections:
        for block in section.blocks:
            if block.id == block_id:
                return (block, section.discipline) if isinstance(block, SimulationBlock) else None
    return None


def _marked(row: PieceRow, user: User, *, hidden: bool, now: datetime) -> bool:
    if hidden == (row.hiddenAt is not None):
        return False
    row.hiddenAt = now if hidden else None
    row.hiddenById = user.id if hidden else None
    return True
