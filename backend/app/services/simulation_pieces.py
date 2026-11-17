from __future__ import annotations

import uuid
from collections.abc import Collection

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgePiece as PieceRow
from app.research.knowledge_pieces import KnowledgePiece
from app.research.piece_reuse import SIMULATION_KIND
from app.research.vocabulary import CANONICAL_LANGUAGE

from .piece_lookup import PIECE_CANDIDATES_MAX, stored_piece

__all__ = ["simulation_pieces"]


async def simulation_pieces(
    session: AsyncSession, claim_ids: Collection[uuid.UUID], facets: Collection[str]
) -> list[KnowledgePiece]:
    if not claim_ids or not facets:
        return []
    rows = await session.scalars(
        select(PieceRow)
        .where(
            PieceRow.kind == SIMULATION_KIND,
            PieceRow.craftId.is_(None),
            PieceRow.language == CANONICAL_LANGUAGE,
            PieceRow.claimIds.contained_by(sorted(claim_ids)),
            or_(
                PieceRow.hiddenAt.is_not(None),
                and_(
                    PieceRow.facet.in_(sorted(facets)),
                    PieceRow.supersededById.is_(None),
                    PieceRow.staleSince.is_(None),
                ),
            ),
        )
        .order_by(PieceRow.createdAt.desc(), PieceRow.id)
        .limit(PIECE_CANDIDATES_MAX)
    )
    return [piece for row in rows.all() if (piece := stored_piece(row)) is not None]
