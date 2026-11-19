from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImageContribution, MediaAsset
from app.research.chapter_keys import CHAPTER_KEYS
from app.research.craft_contributed import CONTRIBUTED_MIMES, CONTRIBUTED_PER_CHAPTER_MAX

__all__ = [
    "APPROVED",
    "CONTRIBUTED_READ_MAX",
    "ContributedRecord",
    "ShownPicture",
    "approved_pictures",
    "shown_contributions",
    "shown_picture",
]

APPROVED = "APPROVED"
SHARED = "CRAFT_SHARED"
CONTRIBUTED_READ_MAX = len(CHAPTER_KEYS) * CONTRIBUTED_PER_CHAPTER_MAX


@dataclass(frozen=True)
class ContributedRecord:
    contribution_id: uuid.UUID
    origin: str
    generator: str | None
    caption: str
    alt_text: str
    stage_id: uuid.UUID | None
    claim_ids: tuple[uuid.UUID, ...]
    mime: str
    width: int
    height: int


@dataclass(frozen=True)
class ShownPicture:
    key: str
    mime: str
    sha256: str


def shown_contributions(craft_id: uuid.UUID | None = None) -> Select[Any]:
    where: list[ColumnElement[bool]] = [_shown()]
    if craft_id is not None:
        where.append(ImageContribution.craftId == craft_id)
    return (
        select(ImageContribution.id)
        .join(MediaAsset, MediaAsset.id == ImageContribution.assetId)
        .where(*where)
        .correlate(None)
    )


async def approved_pictures(session: AsyncSession, craft_id: uuid.UUID) -> tuple[ContributedRecord, ...]:
    rows = (
        await session.execute(
            select(ImageContribution, MediaAsset)
            .join(MediaAsset, MediaAsset.id == ImageContribution.assetId)
            .where(ImageContribution.craftId == craft_id, _shown())
            .order_by(ImageContribution.reviewedAt, ImageContribution.id)
            .limit(CONTRIBUTED_READ_MAX)
        )
    ).all()
    return tuple(_record(row, asset) for row, asset in rows)


async def shown_picture(session: AsyncSession, contribution_id: uuid.UUID) -> ShownPicture | None:
    found = (
        await session.execute(
            select(MediaAsset.s3Key, MediaAsset.mime, ImageContribution.sha256)
            .join(MediaAsset, MediaAsset.id == ImageContribution.assetId)
            .where(ImageContribution.id == contribution_id, _shown())
        )
    ).first()
    if found is None:
        return None
    return ShownPicture(key=found.s3Key, mime=found.mime, sha256=found.sha256)


def _shown() -> ColumnElement[bool]:
    return and_(
        ImageContribution.status == APPROVED,
        ImageContribution.sha256.is_not(None),
        MediaAsset.visibility == SHARED,
        MediaAsset.mime.in_(CONTRIBUTED_MIMES),
        MediaAsset.width.is_not(None),
        MediaAsset.height.is_not(None),
    )


def _record(row: ImageContribution, asset: MediaAsset) -> ContributedRecord:
    return ContributedRecord(
        contribution_id=row.id,
        origin=row.origin,
        generator=row.generator,
        caption=row.caption,
        alt_text=row.altText,
        stage_id=row.stageId,
        claim_ids=tuple(row.claimIds),
        mime=asset.mime,
        width=int(asset.width or 0),
        height=int(asset.height or 0),
    )
