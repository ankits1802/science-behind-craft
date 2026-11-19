from __future__ import annotations

import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.core.roles import PROFESSOR, has_rank
from app.models import Craft, ImageContribution, MediaAsset, Process, ProcessStage, User
from app.research.image_contributions import (
    AI_GENERATED,
    ImageContributionView,
    ImageDeclaration,
    shown_label,
)
from app.research.image_intake import inspected_image
from app.research.retrieval import OPEN_CHUNK_ACLS

from . import knowledge_view
from .naming import PlaceParts, content_disposition, file_name, media_key
from .object_store import ObjectStore

__all__ = [
    "ContributionRefused",
    "UnknownImage",
    "Upload",
    "approve",
    "declare",
    "own_images",
    "queue",
    "receive_file",
    "reject",
    "views",
    "withdraw",
]

AWAITING_FILE = "AWAITING_FILE"
PENDING = "PENDING"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
WITHDRAWN = "WITHDRAWN"
LIVE = (AWAITING_FILE, PENDING, APPROVED)
WITHDRAWABLE = (AWAITING_FILE, PENDING)
APPROVED_STAYS = "An approved picture stays published: the consent to publish it cannot be revoked."
SHARED = "CRAFT_SHARED"
PRIVATE = "PRIVATE"
EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
FILE_WHAT = {"PHOTOGRAPH": "Photo", "DRAWING": "Drawing", AI_GENERATED: "Illustration"}
LINK_SECONDS = 600
LIST_MAX = 100


class UnknownImage(Exception):
    pass


@dataclass(frozen=True)
class Upload:
    contribution_id: uuid.UUID
    user: User
    data: bytes


@dataclass(frozen=True)
class _Decision:
    reviewer: User
    status: str
    note: str | None
    now: datetime


class ContributionRefused(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


async def declare(
    session: AsyncSession, user: User, declaration: ImageDeclaration, *, now: datetime
) -> ImageContribution:
    craft = await knowledge_view.resolve_craft(session, declaration.craft_slug)
    if craft is None:
        raise InvalidInput(f"No craft has the slug {declaration.craft_slug}")
    await _check_stage(session, craft.id, declaration.stage_id)
    await _check_claims(session, declaration.claim_ids)
    row = ImageContribution(
        contributorId=user.id,
        craftId=craft.id,
        stageId=declaration.stage_id,
        claimIds=list(declaration.claim_ids),
        origin=declaration.origin,
        generator=declaration.generator,
        prompt=declaration.prompt,
        caption=declaration.caption,
        altText=declaration.alt_text,
        termsVersion=declaration.terms_version,
        rightsConfirmedAt=now,
        status=AWAITING_FILE,
    )
    session.add(row)
    await session.flush()
    return row


async def receive_file(
    session: AsyncSession, upload: Upload, *, objects: ObjectStore, now: datetime
) -> ImageContribution:
    user = upload.user
    row = await _own(session, upload.contribution_id, user)
    if row.status != AWAITING_FILE:
        raise ContributionRefused("This contribution already has its picture")
    image = inspected_image(upload.data)
    if image.ai_marked and row.origin != AI_GENERATED:
        raise InvalidInput("This file's own metadata says an AI made it. Declare it as AI-generated.")
    digest = hashlib.sha256(image.data).hexdigest()
    await _refuse_repeat(session, digest)
    craft = await session.get(Craft, row.craftId)
    key = media_key(user.id, _leaf(row, craft, image.mime, now))
    await objects.put(key, image.data, content_type=image.mime)
    asset = MediaAsset(
        s3Key=key,
        mime=image.mime,
        bytes=len(image.data),
        width=image.width,
        height=image.height,
        label=row.caption,
        model=row.generator,
        altText=row.altText,
        visibility=PRIVATE,
    )
    session.add(asset)
    await session.flush()
    row.assetId, row.sha256, row.aiMarked, row.status = asset.id, digest, image.ai_marked, PENDING
    if has_rank(user, PROFESSOR):
        _decide(row, asset, _Decision(user, APPROVED, None, now))
    await session.flush()
    return row


async def approve(
    session: AsyncSession, contribution_id: uuid.UUID, reviewer: User, note: str | None, *, now: datetime
) -> ImageContribution:
    row, asset = await _reviewable(session, contribution_id, reviewer)
    _decide(row, asset, _Decision(reviewer, APPROVED, note, now))
    await session.flush()
    return row


async def reject(
    session: AsyncSession, contribution_id: uuid.UUID, reviewer: User, note: str, *, now: datetime
) -> ImageContribution:
    row, asset = await _reviewable(session, contribution_id, reviewer)
    _decide(row, asset, _Decision(reviewer, REJECTED, note, now))
    await session.flush()
    return row


async def withdraw(session: AsyncSession, contribution_id: uuid.UUID, user: User) -> ImageContribution:
    row = await _own(session, contribution_id, user)
    if row.status == APPROVED:
        raise ContributionRefused(APPROVED_STAYS)
    if row.status not in WITHDRAWABLE:
        raise ContributionRefused("This contribution is already closed")
    row.status = WITHDRAWN
    await session.flush()
    return row


async def queue(session: AsyncSession, status: str) -> list[ImageContribution]:
    rows = await session.scalars(
        select(ImageContribution)
        .where(ImageContribution.status == status)
        .order_by(ImageContribution.createdAt, ImageContribution.id)
        .limit(LIST_MAX)
    )
    return list(rows)


async def own_images(session: AsyncSession, user: User) -> list[ImageContribution]:
    rows = await session.scalars(
        select(ImageContribution)
        .where(ImageContribution.contributorId == user.id)
        .order_by(ImageContribution.createdAt.desc(), ImageContribution.id)
        .limit(LIST_MAX)
    )
    return list(rows)


async def views(
    session: AsyncSession, rows: Sequence[ImageContribution], *, objects: ObjectStore | None, now: datetime
) -> list[ImageContributionView]:
    crafts = await _by_id(session, Craft, {row.craftId for row in rows})
    assets = await _by_id(session, MediaAsset, {row.assetId for row in rows if row.assetId is not None})
    return [
        _view(row, crafts[row.craftId], assets.get(row.assetId) if row.assetId else None, objects, now)
        for row in rows
    ]


async def _by_id(session: AsyncSession, model: Any, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, Any]:
    wanted = [found for found in ids if found is not None]
    if not wanted:
        return {}
    return {row.id: row for row in await session.scalars(select(model).where(model.id.in_(wanted)))}


def _view(
    row: ImageContribution, craft: Craft, asset: MediaAsset | None, objects: ObjectStore | None, now: datetime
) -> ImageContributionView:
    return ImageContributionView(
        id=row.id,
        craft_slug=craft.slug,
        craft_name=craft.name,
        stage_id=row.stageId,
        claim_ids=row.claimIds,
        origin=row.origin,
        label=shown_label(row.origin, row.generator),
        generator=row.generator,
        prompt=row.prompt,
        caption=row.caption,
        alt_text=row.altText,
        status=row.status,
        ai_marked=row.aiMarked,
        mime=asset.mime if asset else None,
        width=asset.width if asset else None,
        height=asset.height if asset else None,
        file_url=_link(asset, objects, now),
        created_at=row.createdAt,
        reviewed_at=row.reviewedAt,
        review_note=row.reviewNote,
    )


def _link(asset: MediaAsset | None, objects: ObjectStore | None, now: datetime) -> str | None:
    if asset is None or objects is None:
        return None
    leaf = asset.s3Key.rsplit("/", 1)[-1]
    return objects.presigned_get(
        asset.s3Key, disposition=content_disposition(leaf, inline=True), seconds=LINK_SECONDS, now=now
    ).url


def _decide(row: ImageContribution, asset: MediaAsset | None, decision: _Decision) -> None:
    row.status = decision.status
    row.reviewedById = decision.reviewer.id
    row.reviewedAt = decision.now
    row.reviewNote = decision.note
    if asset is not None:
        approved = decision.status == APPROVED
        asset.visibility = SHARED if approved else PRIVATE
        asset.approvedById = decision.reviewer.id if approved else None


async def _reviewable(
    session: AsyncSession, contribution_id: uuid.UUID, reviewer: User
) -> tuple[ImageContribution, MediaAsset | None]:
    row = await session.get(ImageContribution, contribution_id, with_for_update=True)
    if row is None:
        raise UnknownImage(str(contribution_id))
    if row.status != PENDING:
        raise ContributionRefused("Only a picture waiting for review can be decided")
    if row.contributorId == reviewer.id:
        raise ContributionRefused("A reviewer does not decide their own picture")
    asset = await session.get(MediaAsset, row.assetId) if row.assetId is not None else None
    return row, asset


async def _own(session: AsyncSession, contribution_id: uuid.UUID, user: User) -> ImageContribution:
    row = await session.get(ImageContribution, contribution_id, with_for_update=True)
    if row is None or row.contributorId != user.id:
        raise UnknownImage(str(contribution_id))
    return row


async def _check_stage(session: AsyncSession, craft_id: uuid.UUID, stage_id: uuid.UUID | None) -> None:
    if stage_id is None:
        return
    found = await session.scalar(
        select(ProcessStage.id)
        .join(Process, Process.id == ProcessStage.processId)
        .where(ProcessStage.id == stage_id, Process.craftId == craft_id)
    )
    if found is None:
        raise InvalidInput("That stage is not one of this craft's")


async def _check_claims(session: AsyncSession, claim_ids: Sequence[uuid.UUID]) -> None:
    if not claim_ids:
        return
    shown, _ = await knowledge_view.claims_by_id(session, claim_ids, acls=OPEN_CHUNK_ACLS)
    missing = [claim_id for claim_id in claim_ids if claim_id not in shown]
    if missing:
        raise InvalidInput(f"No shown fact has the id {missing[0]}")


async def _refuse_repeat(session: AsyncSession, digest: str) -> None:
    found = await session.scalar(
        select(ImageContribution.id).where(
            ImageContribution.sha256 == digest, ImageContribution.status.in_(LIVE)
        )
    )
    if found is not None:
        raise ContributionRefused("This picture has been contributed already")


def _leaf(row: ImageContribution, craft: Craft | None, mime: str, now: datetime) -> str:
    return file_name(
        entity="Contribution",
        what=FILE_WHAT[row.origin],
        ext=EXTENSIONS[mime],
        moment=now,
        place=PlaceParts(),
        craft=craft.name if craft else None,
        subject=row.caption,
        sequence=None,
    )
