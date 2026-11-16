from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.core.clock import INDIA_TZ
from app.core.errors import InvalidInput
from app.schemas.media import (
    ASSET_LABEL,
    POLL_SECONDS,
    PRESIGNED_GET_SECONDS,
    REFUNDED_STATUSES,
    MediaAssetView,
    MediaFailure,
    MediaJobView,
    MediaLabel,
    MediaStageRef,
)
from app.services.naming import content_disposition
from app.services.object_store import PresignedGet

from .records import AssetRecord, JobRecord, StageFacts

__all__ = ["FAILURE_MESSAGES", "AssetLinks", "asset_view", "is_cached", "job_view"]

FAILURE_MESSAGES = {
    "FAILED": "Couldn't make this illustration. Try again.",
    "BLOCKED": "This illustration couldn't be made from these facts.",
}
SETTLED_STATUSES = frozenset({"SUCCEEDED", *REFUNDED_STATUSES})


class AssetLinks(Protocol):
    def presigned_get(self, key: str, *, disposition: str, seconds: int, now: datetime) -> PresignedGet: ...


def is_cached(job: JobRecord, asset: AssetRecord | None) -> bool:
    return asset is not None and asset.job_id != job.id


def job_view(
    job: JobRecord, stage: StageFacts, asset: AssetRecord | None, *, links: AssetLinks, now: datetime
) -> MediaJobView:
    if (asset is None) != (job.status != "SUCCEEDED"):
        raise InvalidInput(f"Media job {job.id} is {job.status} with asset {job.asset_id}")
    cached = is_cached(job, asset)
    return MediaJobView(
        id=job.id,
        kind=job.kind,
        status=job.status,
        craft=stage.craft.ref,
        stage=MediaStageRef(id=stage.id, ordinal=stage.ordinal, name=stage.name),
        claim_ids=list(job.claim_ids),
        cached=cached,
        attempts=job.attempts,
        refunded=job.status in REFUNDED_STATUSES and not cached,
        poll_after_seconds=None if job.status in SETTLED_STATUSES else POLL_SECONDS,
        created_at=job.created_at,
        updated_at=job.updated_at,
        asset=None if asset is None else asset_view(asset, links=links, now=now),
        failure=_failure(job.status),
    )


def asset_view(asset: AssetRecord, *, links: AssetLinks, now: datetime) -> MediaAssetView:
    leaf = asset.s3_key.rsplit("/", 1)[-1]
    link = links.presigned_get(
        asset.s3_key,
        disposition=content_disposition(leaf, inline=True),
        seconds=PRESIGNED_GET_SECONDS,
        now=now,
    )
    return MediaAssetView(
        id=asset.id,
        mime=asset.mime,
        width=asset.width,
        height=asset.height,
        duration_seconds=asset.duration_seconds,
        url=link.url,
        url_expires_at=link.expires_at,
        file_name=leaf,
        label=MediaLabel(
            text=ASSET_LABEL,
            model=asset.model,
            generated_on=asset.created_at.astimezone(INDIA_TZ).date().isoformat(),
        ),
        alt_text=asset.alt_text,
        visibility=asset.visibility,
    )


def _failure(status: str) -> MediaFailure | None:
    message = FAILURE_MESSAGES.get(status)
    return None if message is None else MediaFailure(reason=status, message=message)
