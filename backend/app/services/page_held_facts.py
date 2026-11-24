from __future__ import annotations

import uuid
from collections.abc import Collection

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArticleSection, Claim, Concept, CuratedCategoryClaim
from app.retrieval.hybrid import craft_scope
from app.retrieval.statements import family_science, scope_claims

from .open_work_subjects import CATEGORY, WorkSubject

__all__ = ["held_claims"]

CONCEPT_SUBJECT = "CONCEPT"
PUBLISHED = "PUBLISHED"


async def held_claims(
    session: AsyncSession, subject: WorkSubject, claim_ids: Collection[uuid.UUID]
) -> frozenset[uuid.UUID]:
    wanted = list(dict.fromkeys(claim_ids))
    if not wanted:
        return frozenset()
    scoped = await session.scalars(
        select(Claim.id).where(Claim.id.in_(wanted), await _held_by(session, subject))
    )
    written = await _section_claims(session, subject)
    return frozenset(scoped.all()) | frozenset(claim for claim in wanted if claim in written)


async def _held_by(session: AsyncSession, subject: WorkSubject) -> ColumnElement[bool]:
    if subject.kind != CATEGORY:
        return scope_claims(await craft_scope(session, subject.slug))
    curated = select(CuratedCategoryClaim.claimId).where(CuratedCategoryClaim.categoryId == subject.id)
    science = select(Concept.id).where(family_science(subject.id))
    return or_(
        Claim.id.in_(curated), and_(Claim.subjectType == CONCEPT_SUBJECT, Claim.subjectId.in_(science))
    )


async def _section_claims(session: AsyncSession, subject: WorkSubject) -> set[uuid.UUID]:
    owner = ArticleSection.categoryId if subject.kind == CATEGORY else ArticleSection.craftId
    rows = await session.scalars(
        select(ArticleSection.sentences).where(owner == subject.id, ArticleSection.status == PUBLISHED)
    )
    return {
        uuid.UUID(str(claim))
        for sentences in rows.all()
        for sentence in sentences
        for claim in sentence.get("claimIds") or ()
    }
