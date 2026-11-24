from __future__ import annotations

import uuid
from datetime import datetime
from types import MappingProxyType
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import Craft, ImageContribution, MediaAsset, User
from app.research.image_contributions import PictureTarget
from app.research.published_edits import PictureEdit
from app.research.review_labels import cut_label
from app.research.staged_reviews import EDIT, REMOVE, StagedDecision

from . import audit
from .contributed_pictures import shown_contributions
from .image_contributions_checks import checked_target
from .open_work_subjects import CATEGORY
from .page_revalidation import craft_owners
from .published_kinds import (
    NO_ITEM,
    Carried,
    Editable,
    PublishedKind,
    PublishedLine,
    PublishedQuery,
    PublishedRef,
    checked_edit,
)

__all__ = ["PICTURE_EDITED", "PICTURE_REMOVED", "PUBLISHED_PICTURES"]

PICTURE_REMOVED = "picture.removed"
PICTURE_EDITED = "picture.edited"
TARGET = "ImageContribution"
PRIVATE = "PRIVATE"
REMOVED = "Removed: the picture is off its craft's pages and no longer served; its record, credit and file are kept."
EDITED = "Edited: the picture is shown as changed on its craft's pages, and its earlier values are kept in the record."
CRAFT_PAGES = "Pictures are given to a craft's page; name the craft whose pictures to list."
COLUMNS = {"caption": "caption", "alt_text": "altText", "focal": "focal"}


async def _picture(
    session: AsyncSession, picture_id: uuid.UUID, *, lock: bool = False
) -> ImageContribution | None:
    query = select(ImageContribution).where(
        ImageContribution.id == picture_id, ImageContribution.id.in_(shown_contributions())
    )
    return await session.scalar(
        query.with_for_update(of=ImageContribution).execution_options(populate_existing=True)
        if lock
        else query
    )


async def _name(session: AsyncSession, ref: PublishedRef) -> str | None:
    row = await _picture(session, ref.id)
    return None if row is None else cut_label(f"Picture: {row.caption}")


def _current(row: ImageContribution) -> dict[str, Any]:
    place = PictureTarget.model_validate(
        {"stage_id": row.stageId, "material_id": row.materialId, "slot": row.slot}
    )
    return {
        "caption": row.caption,
        "alt_text": row.altText,
        "focal": row.focal,
        "place": place.model_dump(mode="json", by_alias=False),
    }


async def _editable(session: AsyncSession, ref: PublishedRef) -> Editable | None:
    row = await _picture(session, ref.id)
    return None if row is None else Editable(_current(row), PictureEdit)


async def _shown(session: AsyncSession, decision: StagedDecision) -> ImageContribution:
    row = await _picture(session, decision.id, lock=True)
    if row is None:
        raise InvalidInput(NO_ITEM.format(kind="picture", id=decision.id))
    return row


async def _remove(session: AsyncSession, decision: StagedDecision, reviewer: User, _now: datetime) -> Carried:
    row = await _shown(session, decision)
    asset = await session.get(MediaAsset, row.assetId, with_for_update=True, populate_existing=True)
    if asset is None:
        raise InvalidInput(NO_ITEM.format(kind="picture", id=decision.id))
    asset.visibility = PRIVATE
    await audit.record(
        session,
        action=PICTURE_REMOVED,
        actor=reviewer,
        target_type=TARGET,
        target_id=row.id,
        detail={"caption": row.caption, "asset": str(asset.id), "reason": decision.reason},
    )
    await session.flush()
    return Carried(REMOVED, await craft_owners(session, [row.craftId]))


async def _edit(session: AsyncSession, decision: StagedDecision, reviewer: User, _now: datetime) -> Carried:
    row = await _shown(session, decision)
    before = _current(row)
    fields = checked_edit(decision, Editable(before, PictureEdit))
    if "place" in fields:
        craft = await session.get(Craft, row.craftId)
        if craft is None:
            raise InvalidInput(NO_ITEM.format(kind="picture", id=decision.id))
        place = await checked_target(session, craft, PictureTarget.model_validate(fields["place"]))
        row.stageId, row.materialId, row.slot = place.stage_id, place.material_id, place.slot
    for name, column in COLUMNS.items():
        if name in fields:
            setattr(row, column, fields[name])
    await audit.record(
        session,
        action=PICTURE_EDITED,
        actor=reviewer,
        target_type=TARGET,
        target_id=row.id,
        detail={"before": {name: before[name] for name in fields}, "reason": decision.reason},
    )
    await session.flush()
    return Carried(EDITED, await craft_owners(session, [row.craftId]))


async def _listed(session: AsyncSession, query: PublishedQuery) -> list[PublishedLine]:
    if query.page is None or query.page.kind == CATEGORY:
        raise InvalidInput(CRAFT_PAGES)
    rows = await session.execute(
        select(ImageContribution.id, ImageContribution.caption)
        .where(ImageContribution.id.in_(shown_contributions(query.page.id)))
        .order_by(ImageContribution.reviewedAt, ImageContribution.id)
        .offset(query.offset)
        .limit(query.limit)
    )
    return [PublishedLine(picture_id, cut_label(f"Picture: {caption}")) for picture_id, caption in rows.all()]


PUBLISHED_PICTURES = PublishedKind(
    noun="picture",
    name=_name,
    actions=MappingProxyType({REMOVE: _remove, EDIT: _edit}),
    listed=_listed,
    editable=_editable,
)
