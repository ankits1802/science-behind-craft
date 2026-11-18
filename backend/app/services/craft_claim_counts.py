from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Claim, Concept
from app.research.retrieval import MODE_CLAIM_LEVELS, MODE_CLAIM_STATUSES, VISIBLE_SENSITIVITY

__all__ = ["craft_claim_counts"]

CONCEPT_SUBJECT = "CONCEPT"


async def craft_claim_counts(
    session: AsyncSession, craft_ids: Sequence[uuid.UUID] | None = None, *, mode: str
) -> dict[uuid.UUID, int]:
    if craft_ids is not None and not craft_ids:
        return {}
    statement = (
        select(Concept.craftId, func.count(Claim.id))
        .join(Concept, and_(Claim.subjectType == CONCEPT_SUBJECT, Claim.subjectId == Concept.id))
        .where(
            Concept.craftId.is_not(None),
            Concept.sensitivity == VISIBLE_SENSITIVITY,
            Claim.status.in_(MODE_CLAIM_STATUSES[mode]),
            Claim.evidenceLevel.in_(MODE_CLAIM_LEVELS[mode]),
            Claim.sensitivity == VISIBLE_SENSITIVITY,
        )
        .group_by(Concept.craftId)
    )
    if craft_ids is not None:
        statement = statement.where(Concept.craftId.in_(list(craft_ids)))
    return {row[0]: int(row[1]) for row in (await session.execute(statement)).all()}
