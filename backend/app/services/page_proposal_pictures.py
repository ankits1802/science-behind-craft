from __future__ import annotations

import base64
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.models import DrawnPicture, PagePreview, PageProposal, User
from app.research.page_proposal_review import AFTER, DrawnPictureView
from app.research.page_render import RenderedImage

from .page_preview_links import preview_key, preview_token, token_preview

__all__ = [
    "PICTURE_PATH",
    "drawn_picture",
    "keep_drawn_pictures",
    "kept_pictures",
    "move_preview_pictures",
    "picture_views",
    "store_side",
]

PICTURE_PATH = "/api/review-queue/pages/{id}/pictures/{side}/{name}"


async def keep_drawn_pictures(
    session: AsyncSession, user: User, preview_url: str, images: Sequence[RenderedImage], *, now: datetime
) -> None:
    preview_id = token_preview(preview_token(preview_url), user.id, preview_key(), now=now)
    row = await session.get(PagePreview, preview_id)
    if row is None or not images:
        return
    others = select(PagePreview.id).where(
        PagePreview.userId == user.id,
        PagePreview.subjectKind == row.subjectKind,
        PagePreview.subjectSlug == row.subjectSlug,
    )
    await session.execute(delete(DrawnPicture).where(DrawnPicture.previewId.in_(others)))
    session.add_all(_picture(image, AFTER, preview_id=row.id) for image in images)
    await session.flush()


async def move_preview_pictures(
    session: AsyncSession, proposal: PageProposal, after: dict[str, Any] | None, *, now: datetime
) -> int:
    if after is None:
        return 0
    latest = await session.scalar(
        select(PagePreview)
        .where(
            PagePreview.userId == proposal.userId,
            PagePreview.subjectKind == proposal.subjectKind,
            PagePreview.subjectSlug == proposal.subjectSlug,
            PagePreview.expiresAt > now,
        )
        .order_by(PagePreview.createdAt.desc())
        .limit(1)
    )
    if latest is None or latest.document != after:
        return 0
    moved = await session.execute(
        update(DrawnPicture)
        .where(DrawnPicture.previewId == latest.id)
        .values(previewId=None, proposalId=proposal.id)
    )
    await session.flush()
    return int(moved.rowcount or 0)


async def store_side(
    session: AsyncSession, proposal_id: uuid.UUID, side: str, images: Sequence[RenderedImage]
) -> None:
    await session.execute(
        delete(DrawnPicture).where(DrawnPicture.proposalId == proposal_id, DrawnPicture.side == side)
    )
    session.add_all(_picture(image, side, proposal_id=proposal_id) for image in images)
    await session.flush()


async def picture_views(session: AsyncSession, proposal_id: uuid.UUID) -> list[DrawnPictureView]:
    rows = await session.scalars(
        select(DrawnPicture)
        .where(DrawnPicture.proposalId == proposal_id)
        .order_by(DrawnPicture.side.desc(), DrawnPicture.createdAt, DrawnPicture.name)
    )
    return [
        DrawnPictureView.model_validate(
            {
                "side": row.side,
                "name": row.name,
                "caption": row.caption,
                "width": row.width,
                "height": row.height,
                "url": PICTURE_PATH.format(id=proposal_id, side=row.side, name=row.name),
            }
        )
        for row in rows
    ]


async def drawn_picture(
    session: AsyncSession, proposal_id: uuid.UUID, side: str, name: str
) -> DrawnPicture | None:
    return await session.scalar(
        select(DrawnPicture)
        .options(undefer(DrawnPicture.data))
        .where(DrawnPicture.proposalId == proposal_id, DrawnPicture.side == side, DrawnPicture.name == name)
        .limit(1)
    )


async def kept_pictures(session: AsyncSession, proposal_id: uuid.UUID) -> list[DrawnPicture]:
    rows = await session.scalars(
        select(DrawnPicture)
        .options(undefer(DrawnPicture.data))
        .where(DrawnPicture.proposalId == proposal_id)
        .order_by(DrawnPicture.createdAt, DrawnPicture.name)
    )
    return list(rows.all())


def _picture(
    image: RenderedImage,
    side: str,
    *,
    preview_id: uuid.UUID | None = None,
    proposal_id: uuid.UUID | None = None,
) -> DrawnPicture:
    return DrawnPicture(
        previewId=preview_id,
        proposalId=proposal_id,
        side=side,
        name=image.name,
        caption=image.caption,
        width=image.width,
        height=image.height,
        data=base64.b64decode(image.data, validate=True),
    )
