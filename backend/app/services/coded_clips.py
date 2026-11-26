from __future__ import annotations

import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import INDIA_TZ
from app.models import MediaAsset, MediaJob
from app.research.component_specs_science_coded import CodedFigureSpec, CodedFilm

__all__ = [
    "CLIP_KIND",
    "ClipPlacement",
    "SharedClip",
    "clip_credit",
    "filmed_spec",
    "shared_clip",
    "shared_clips",
]

CLIP_KIND = "VIDEO"
SHARED = "CRAFT_SHARED"
SUCCEEDED = "SUCCEEDED"
CREDIT = "AI video, made with {model} on {day}"
NOT_HELD = (
    "the film {key} names the clip {clip}, which is not a clip this page holds: name an approved video of the "
    "media store made from a fact the figure cites"
)


@dataclass(frozen=True)
class SharedClip:
    asset_id: uuid.UUID
    page_key: str
    mime: str
    model: str
    made_at: datetime
    duration_seconds: float | None
    claim_ids: frozenset[uuid.UUID]


@dataclass(frozen=True)
class ClipPlacement:
    problems: list[str] = field(default_factory=list)
    spec: dict[str, Any] | None = None
    clips: tuple[SharedClip, ...] = ()


def clip_credit(clip: SharedClip) -> str:
    return CREDIT.format(model=clip.model, day=clip.made_at.astimezone(INDIA_TZ).date().isoformat())


async def shared_clips(
    session: AsyncSession, asset_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, SharedClip]:
    wanted = list(dict.fromkeys(asset_ids))
    if not wanted:
        return {}
    rows = await session.execute(
        select(MediaAsset, MediaJob)
        .join(MediaJob, MediaJob.id == MediaAsset.jobId)
        .where(
            MediaAsset.id.in_(wanted),
            MediaJob.kind == CLIP_KIND,
            MediaJob.status == SUCCEEDED,
            MediaAsset.visibility == SHARED,
            MediaAsset.pageKey.is_not(None),
        )
    )
    found = (_clip(asset, job) for asset, job in rows.tuples())
    return {clip.asset_id: clip for clip in found if clip is not None}


async def shared_clip(session: AsyncSession, asset_id: uuid.UUID) -> SharedClip | None:
    return (await shared_clips(session, [asset_id])).get(asset_id)


async def filmed_spec(
    session: AsyncSession, checked: object, claim_ids: Sequence[uuid.UUID]
) -> ClipPlacement:
    if not isinstance(checked, CodedFigureSpec) or not checked.films:
        return ClipPlacement()
    clips = await shared_clips(session, [film.clip for film in checked.films if film.clip is not None])
    cited = frozenset(claim_ids)
    problems = [
        NOT_HELD.format(key=film.key, clip=film.clip)
        for film in checked.films
        if film.clip is not None and not _held(clips.get(film.clip), cited)
    ]
    if problems:
        return ClipPlacement(problems=problems)
    films = [_credited(film, clips) for film in checked.films]
    held = tuple(dict.fromkeys(clips[film.clip] for film in checked.films if film.clip is not None))
    return ClipPlacement(spec=checked.model_copy(update={"films": films}).model_dump(mode="json"), clips=held)


def _held(clip: SharedClip | None, cited: frozenset[uuid.UUID]) -> bool:
    return clip is not None and bool(clip.claim_ids & cited)


def _credited(film: CodedFilm, clips: dict[uuid.UUID, SharedClip]) -> CodedFilm:
    clip = clips.get(film.clip) if film.clip is not None else None
    return film.model_copy(update={"credit": None if clip is None else clip_credit(clip)})


def _clip(asset: MediaAsset, job: MediaJob) -> SharedClip | None:
    model = asset.model or job.model
    if asset.pageKey is None or not model or not (asset.altText or "").strip():
        return None
    return SharedClip(
        asset_id=asset.id,
        page_key=asset.pageKey,
        mime=asset.mime,
        model=model,
        made_at=asset.createdAt,
        duration_seconds=None if asset.durationS is None else float(asset.durationS),
        claim_ids=frozenset(job.claimIds or ()),
    )
