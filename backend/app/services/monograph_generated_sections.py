from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArticleSection
from app.research.article_sections import SectionSentence

__all__ = [
    "PERSON",
    "PUBLISHED",
    "SUPERSEDED",
    "ReviewedBy",
    "SectionOwner",
    "publish_reviewed_section",
    "publish_section",
    "published_section",
    "retire_sections",
]

PUBLISHED = "PUBLISHED"
SUPERSEDED = "SUPERSEDED"
PERSON = "USER"
CRAFT_COLUMN = "craftId"
CATEGORY_COLUMN = "categoryId"


@dataclass(frozen=True)
class SectionOwner:
    column: str
    id: uuid.UUID

    @classmethod
    def craft(cls, craft_id: uuid.UUID) -> SectionOwner:
        return cls(CRAFT_COLUMN, craft_id)

    @classmethod
    def category(cls, category_id: uuid.UUID) -> SectionOwner:
        return cls(CATEGORY_COLUMN, category_id)

    def owns(self) -> ColumnElement[bool]:
        column: Any = ArticleSection.categoryId if self.column == CATEGORY_COLUMN else ArticleSection.craftId
        return column == self.id


@dataclass(frozen=True)
class ReviewedBy:
    writer_id: uuid.UUID | None
    reviewer_id: uuid.UUID
    at: datetime


async def published_section(session: AsyncSession, owner: SectionOwner, field: str) -> ArticleSection | None:
    return await session.scalar(
        select(ArticleSection).where(
            owner.owns(), ArticleSection.field == field, ArticleSection.status == PUBLISHED
        )
    )


async def publish_section(
    session: AsyncSession, owner: SectionOwner, field: str, sentences: Sequence[SectionSentence]
) -> bool:
    stored = _stored(sentences)
    current = await published_section(session, owner, field)
    if current is not None and (current.sentences == stored or current.writtenByKind == PERSON):
        return False
    await _replace(session, owner, current, ArticleSection(field=field, sentences=stored, status=PUBLISHED))
    return True


async def publish_reviewed_section(
    session: AsyncSession,
    owner: SectionOwner,
    field: str,
    sentences: Sequence[SectionSentence],
    reviewed: ReviewedBy,
) -> uuid.UUID:
    row = ArticleSection(
        id=uuid.uuid4(),
        field=field,
        sentences=_stored(sentences),
        status=PUBLISHED,
        writtenByKind=PERSON,
        writtenById=reviewed.writer_id,
        reviewedById=reviewed.reviewer_id,
        reviewedAt=reviewed.at,
    )
    await _replace(session, owner, await published_section(session, owner, field), row)
    await session.flush()
    return row.id


async def retire_sections(session: AsyncSession, owner: SectionOwner, kept: Collection[str]) -> list[str]:
    rows = await session.scalars(
        select(ArticleSection).where(
            owner.owns(),
            ArticleSection.status == PUBLISHED,
            ArticleSection.field.not_in(sorted(kept)),
            ArticleSection.writtenByKind != PERSON,
        )
    )
    retired = []
    for row in rows.all():
        row.status = SUPERSEDED
        retired.append(row.field)
    if retired:
        await session.flush()
    return sorted(retired)


async def _replace(
    session: AsyncSession, owner: SectionOwner, current: ArticleSection | None, row: ArticleSection
) -> None:
    latest = await session.scalar(
        select(func.max(ArticleSection.version)).where(owner.owns(), ArticleSection.field == row.field)
    )
    if current is not None:
        current.status = SUPERSEDED
        await session.flush()
    setattr(row, owner.column, owner.id)
    row.version = (latest or 0) + 1
    session.add(row)


def _stored(sentences: Sequence[SectionSentence]) -> list[dict[str, Any]]:
    return [sentence.model_dump(mode="json", by_alias=True) for sentence in sentences]
