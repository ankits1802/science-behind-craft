from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OpenPicture
from app.research.open_pictures import OpenSource

__all__ = ["open_source_of", "open_sources", "stored_open_picture"]


def stored_open_picture(contribution_id: uuid.UUID, source: OpenSource) -> OpenPicture:
    return OpenPicture(
        contributionId=contribution_id,
        site=source.site,
        pageUrl=source.page_url,
        fileUrl=source.file_url,
        recordUrl=source.record_url,
        title=source.title,
        author=source.author,
        licence=source.licence,
        licenceUrl=source.licence_url,
        credit=source.credit,
        width=source.width,
        height=source.height,
        readAt=source.read_at,
    )


def open_source_of(row: OpenPicture) -> OpenSource:
    return OpenSource(
        site=row.site,
        page_url=row.pageUrl,
        file_url=row.fileUrl,
        record_url=row.recordUrl,
        title=row.title,
        author=row.author,
        licence=row.licence,
        licence_url=row.licenceUrl,
        credit=row.credit,
        width=row.width,
        height=row.height,
        read_at=row.readAt,
    )


async def open_sources(
    session: AsyncSession, contribution_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, OpenSource]:
    if not contribution_ids:
        return {}
    rows = await session.scalars(
        select(OpenPicture).where(OpenPicture.contributionId.in_(list(contribution_ids)))
    )
    return {row.contributionId: open_source_of(row) for row in rows}
