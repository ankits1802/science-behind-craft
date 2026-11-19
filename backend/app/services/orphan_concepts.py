from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, and_, delete, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog,
    Claim,
    Concept,
    ConceptEdge,
    KnowledgePieceSubject,
    Material,
    ProcessStage,
    TermConcept,
)

from . import audit
from .claim_writer import LIVE_CONCEPT_ORIGIN

__all__ = [
    "ORPHANS_PER_NIGHT",
    "ORPHAN_MIN_AGE",
    "REMOVABLE_ORIGINS",
    "OrphanConcept",
    "OrphansReport",
    "orphan_concepts",
    "remove_orphan_concepts",
    "sweep_orphans",
]

ORPHANS_PER_NIGHT = 500
ORPHAN_MIN_AGE = timedelta(days=7)
REMOVABLE_ORIGINS = (LIVE_CONCEPT_ORIGIN,)
CONCEPT_SUBJECT = "CONCEPT"
ORPHANS_REPORTED = "upkeep.orphans_reported"
REPORTED_KEY = "conceptIds"


@dataclass(frozen=True)
class OrphanConcept:
    concept_id: uuid.UUID
    name: str
    type: str
    craft_id: uuid.UUID | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.concept_id),
            "name": self.name,
            "type": self.type,
            "craftId": str(self.craft_id) if self.craft_id else None,
        }


@dataclass
class OrphansReport:
    found: list[OrphanConcept] = field(default_factory=list)
    removed: int = 0
    reported: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "orphansFound": len(self.found),
            "orphansRemoved": self.removed,
            "orphansReported": len(self.reported),
            "orphans": [orphan.as_dict() for orphan in self.found],
        }


def orphaned(now: datetime) -> ColumnElement[bool]:
    return and_(
        Concept.originRef.in_(REMOVABLE_ORIGINS),
        Concept.createdAt < now - ORPHAN_MIN_AGE,
        ~exists().where(Claim.subjectType == CONCEPT_SUBJECT, Claim.subjectId == Concept.id),
        ~exists().where(or_(ConceptEdge.srcId == Concept.id, ConceptEdge.dstId == Concept.id)),
        ~exists().where(ProcessStage.conceptId == Concept.id),
        ~exists().where(Material.conceptId == Concept.id),
        ~exists().where(KnowledgePieceSubject.conceptId == Concept.id),
        ~exists().where(TermConcept.conceptId == Concept.id),
    )


async def orphan_concepts(
    session: AsyncSession, *, now: datetime, limit: int = ORPHANS_PER_NIGHT
) -> list[OrphanConcept]:
    rows = await session.execute(
        select(Concept.id, Concept.name, Concept.type, Concept.craftId)
        .where(orphaned(now))
        .order_by(Concept.createdAt, Concept.id)
        .limit(limit)
    )
    return [OrphanConcept(row.id, row.name, row.type, row.craftId) for row in rows.all()]


async def remove_orphan_concepts(
    session: AsyncSession, orphans: Sequence[OrphanConcept], *, now: datetime
) -> int:
    if not orphans:
        return 0
    ids = [orphan.concept_id for orphan in orphans]
    removed = await session.execute(
        delete(Concept).where(Concept.id.in_(ids), orphaned(now)).returning(Concept.id)
    )
    return len(removed.all())


async def sweep_orphans(session: AsyncSession, *, now: datetime) -> OrphansReport:
    found = await orphan_concepts(session, now=now)
    earlier = await _reported_before(session)
    report = OrphansReport(found=found)
    report.removed = await remove_orphan_concepts(
        session, [orphan for orphan in found if orphan.concept_id in earlier], now=now
    )
    report.reported = [str(orphan.concept_id) for orphan in found if orphan.concept_id not in earlier]
    await audit.record(session, action=ORPHANS_REPORTED, detail={REPORTED_KEY: report.reported})
    await session.commit()
    return report


async def _reported_before(session: AsyncSession) -> set[uuid.UUID]:
    detail = await session.scalar(
        select(AuditLog.detail)
        .where(AuditLog.action == ORPHANS_REPORTED)
        .order_by(AuditLog.createdAt.desc())
        .limit(1)
    )
    listed = (detail or {}).get(REPORTED_KEY) or []
    return {uuid.UUID(value) for value in listed}
