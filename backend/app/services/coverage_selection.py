from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Claim, Concept, Craft, EnrichmentJob
from app.research.crafts import CraftRef
from app.research.planning import FACET_COVERED_MIN_CLAIMS
from app.research.retrieval import HIDDEN_CLAIM_STATUSES, VISIBLE_SENSITIVITY

__all__ = [
    "ENRICHMENT_COOLDOWN",
    "STANDARD_QUESTIONS",
    "CraftToEnrich",
    "StandardQuestion",
    "least_covered_crafts",
    "open_questions",
]

ENRICHMENT_COOLDOWN = timedelta(days=7)
ACTIVE_CRAFT = "ACTIVE"


@dataclass(frozen=True)
class StandardQuestion:
    facet: str
    template: str

    def text_for(self, craft_name: str) -> str:
        return self.template.format(name=craft_name)


STANDARD_QUESTIONS: tuple[StandardQuestion, ...] = (
    StandardQuestion("MATERIAL", "What raw materials, dyes and chemicals are used in {name}?"),
    StandardQuestion("PROCESS_STAGE", "What are the stages of making {name}, in order?"),
    StandardQuestion("MECHANISM", "What chemical or physical changes take place while {name} is made?"),
    StandardQuestion("TOOL", "What tools and equipment are used to make {name}?"),
    StandardQuestion("ENVIRONMENTAL_CONDITION", "How do local water, soil and climate affect {name}?"),
    StandardQuestion("HISTORICAL_CONTEXT", "Where and when did {name} develop, and how has it changed?"),
)


@dataclass(frozen=True)
class CraftToEnrich:
    craft_id: uuid.UUID
    slug: str
    name: str
    claims: int
    facet_claims: Mapping[str, int] = field(default_factory=dict)

    @property
    def ref(self) -> CraftRef:
        return CraftRef(slug=self.slug, name=self.name, path=f"/crafts/{self.slug}")


def open_questions(craft: CraftToEnrich) -> list[StandardQuestion]:
    return [
        question
        for question in STANDARD_QUESTIONS
        if craft.facet_claims.get(question.facet, 0) < FACET_COVERED_MIN_CLAIMS
    ]


async def least_covered_crafts(session: AsyncSession, *, now: datetime, limit: int) -> list[CraftToEnrich]:
    if limit < 1:
        raise ValueError(f"Pick at least one craft, not {limit}")
    counted = _counted_claims().subquery()
    recent = select(EnrichmentJob.id).where(
        EnrichmentJob.craftId == Craft.id, EnrichmentJob.createdAt >= now - ENRICHMENT_COOLDOWN
    )
    rows = await session.execute(
        select(Craft.id, Craft.slug, Craft.name, func.coalesce(func.sum(counted.c.claims), 0).label("claims"))
        .outerjoin(counted, counted.c.craftId == Craft.id)
        .where(Craft.status == ACTIVE_CRAFT, Craft.isCatchAll.is_(False), ~recent.exists())
        .group_by(Craft.id, Craft.slug, Craft.name)
        .order_by("claims", Craft.slug)
    )
    facets = await _facet_claims(session)
    crafts = [
        CraftToEnrich(row.id, row.slug, row.name, int(row.claims), facets.get(row.id, {})) for row in rows
    ]
    return [craft for craft in crafts if open_questions(craft)][:limit]


def _counted_claims() -> Select[tuple[uuid.UUID, str, int]]:
    visible = and_(
        Claim.subjectType == "CONCEPT",
        Claim.subjectId == Concept.id,
        Claim.status.not_in(HIDDEN_CLAIM_STATUSES),
        Claim.sensitivity == VISIBLE_SENSITIVITY,
    )
    return (
        select(Concept.craftId, Concept.type, func.count(Claim.id).label("claims"))
        .join(Claim, visible)
        .where(Concept.craftId.is_not(None), Concept.sensitivity == VISIBLE_SENSITIVITY)
        .group_by(Concept.craftId, Concept.type)
    )


async def _facet_claims(session: AsyncSession) -> dict[uuid.UUID, dict[str, int]]:
    counts: dict[uuid.UUID, dict[str, int]] = {}
    for row in await session.execute(_counted_claims()):
        counts.setdefault(row.craftId, {})[row.type] = int(row.claims)
    return counts
