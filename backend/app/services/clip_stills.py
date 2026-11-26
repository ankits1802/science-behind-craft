from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import uuid
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Protocol

from app.core.errors import AppError, InvalidInput
from app.core.programs import FFMPEG, run_program

from .coded_clips import SharedClip
from .naming import clip_still_key

__all__ = [
    "CUT_SECONDS",
    "STILL_MIME",
    "CutStill",
    "StillObjects",
    "clip_still",
    "delivered_stills",
    "ffmpeg_still",
    "still_args",
]

logger = logging.getLogger(__name__)

STILL_MIME = "image/jpeg"
CUT_SECONDS = 20.0
JPEG_START = b"\xff\xd8\xff"
JPEG_QUALITY = "3"
NO_STILL = "ffmpeg gave no still of the clip"

CutStill = Callable[[bytes, float], Awaitable[bytes]]


class StillObjects(Protocol):
    async def get(self, key: str) -> bytes | None: ...

    async def put(self, key: str, body: bytes, *, content_type: str) -> None: ...


def still_args(path: str, at_seconds: float) -> tuple[str, ...]:
    return (
        FFMPEG,
        "-hide_banner",
        "-nostats",
        "-v",
        "error",
        "-ss",
        f"{at_seconds:.3f}",
        "-i",
        path,
        "-frames:v",
        "1",
        "-an",
        "-f",
        "image2pipe",
        "-c:v",
        "mjpeg",
        "-q:v",
        JPEG_QUALITY,
        "pipe:1",
    )


async def ffmpeg_still(clip: bytes, at_seconds: float) -> bytes:
    folder = Path(await asyncio.to_thread(tempfile.mkdtemp, prefix="kv-clip-"))
    try:
        path = folder / "clip.mp4"
        await asyncio.to_thread(path.write_bytes, clip)
        code, still = await run_program(still_args(str(path), at_seconds), b"", seconds=CUT_SECONDS)
    finally:
        await asyncio.to_thread(shutil.rmtree, folder, True)
    if code != 0 or not still.startswith(JPEG_START):
        raise InvalidInput(NO_STILL)
    return still


async def clip_still(
    objects: StillObjects, clip: SharedClip, *, cut: CutStill = ffmpeg_still
) -> bytes | None:
    try:
        key = clip_still_key(clip.page_key)
    except InvalidInput:
        logger.warning("clip %s has a page copy no still can be filed beside", clip.asset_id)
        return None
    kept = await objects.get(key)
    if kept is not None:
        return kept
    data = await objects.get(clip.page_key)
    if data is None:
        logger.warning("clip %s has no stored page copy, so it has no still", clip.asset_id)
        return None
    try:
        still = await cut(data, (clip.duration_seconds or 0.0) / 2)
    except (AppError, TimeoutError) as failed:
        logger.warning("no still could be cut from clip %s: %s", clip.asset_id, type(failed).__name__)
        return None
    await objects.put(key, still, content_type=STILL_MIME)
    return still


async def delivered_stills(
    objects: StillObjects | None, clips: Sequence[SharedClip], *, cut: CutStill | None = None
) -> list[uuid.UUID]:
    if objects is None:
        if clips:
            logger.warning("no media bucket, so %d delivered clips wait for their stills", len(clips))
        return []
    held = []
    for clip in clips:
        try:
            still = await clip_still(objects, clip, cut=cut or ffmpeg_still)
        except AppError as failed:
            logger.warning("the still of clip %s was not cut at delivery: %s", clip.asset_id, failed)
            continue
        if still is not None:
            held.append(clip.asset_id)
    return held
