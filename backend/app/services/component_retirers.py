from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import Capability, can
from app.models import ComponentProposal, CraftSteward, KnowledgePiece, User

__all__ = ["may_retire", "proposal_of"]


def proposal_of(piece: KnowledgePiece) -> uuid.UUID | None:
    payload = piece.payload if isinstance(piece.payload, dict) else {}
    try:
        return uuid.UUID(str(payload["proposalId"]))
    except KeyError, ValueError:
        return None


async def may_retire(session: AsyncSession, user: User, piece: KnowledgePiece) -> bool:
    if can(user, Capability.REVIEW_CONTRIBUTIONS):
        return True
    proposal_id = proposal_of(piece)
    if proposal_id is not None:
        proposer = await session.scalar(
            select(ComponentProposal.proposerId).where(ComponentProposal.id == proposal_id)
        )
        if proposer == user.id:
            return True
    if piece.craftId is None:
        return False
    steward = await session.scalar(
        select(CraftSteward.id).where(
            CraftSteward.userId == user.id,
            CraftSteward.craftId == piece.craftId,
            CraftSteward.droppedAt.is_(None),
        )
    )
    return steward is not None
