from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

from app.core.errors import AppError

__all__ = [
    "PICTURE_MAX_PIXELS",
    "PICTURE_MAX_SIDE",
    "PICTURE_READS_AT_ONCE",
    "ExportPictures",
    "Picture",
    "PictureAsk",
    "PictureSource",
    "export_pictures",
    "normalised",
]

logger = logging.getLogger(__name__)

PICTURE_MAX_SIDE = 1600
PICTURE_MAX_PIXELS = 40_000_000
PICTURE_READS_AT_ONCE = 4
JPEG_QUALITY = 85
WHITE = (255, 255, 255)


@dataclass(frozen=True)
class Picture:
    data: bytes
    width: int
    height: int


@dataclass(frozen=True)
class ExportPictures:
    found: Mapping[uuid.UUID, Picture]
    unread: frozenset[uuid.UUID] = frozenset()


class PictureSource(Protocol):
    async def picture(self, url: str) -> bytes: ...


class PictureAsk(Protocol):
    @property
    def id(self) -> uuid.UUID: ...

    @property
    def image_url(self) -> str: ...


async def export_pictures(
    medias: Iterable[PictureAsk], source: PictureSource, *, within: float | None = None
) -> ExportPictures:
    wanted: dict[uuid.UUID, PictureAsk] = {}
    for media in medias:
        wanted.setdefault(media.id, media)
    reads = asyncio.Semaphore(PICTURE_READS_AT_ONCE)
    raws = await asyncio.gather(*(_read(media, source, reads, within) for media in wanted.values()))
    found: dict[uuid.UUID, Picture] = {}
    unread: set[uuid.UUID] = set()
    for media, raw in zip(wanted.values(), raws, strict=True):
        if raw is None:
            unread.add(media.id)
            continue
        picture = await asyncio.to_thread(normalised, raw)
        if picture is None:
            logger.warning("picture %s is not an image a document can hold", media.id)
            continue
        found[media.id] = picture
    return ExportPictures(found=found, unread=frozenset(unread))


async def _read(
    media: PictureAsk, source: PictureSource, reads: asyncio.Semaphore, within: float | None
) -> bytes | None:
    async with reads:
        try:
            async with asyncio.timeout(within):
                return await source.picture(media.image_url)
        except (AppError, TimeoutError) as error:
            logger.warning(
                "picture %s is left out of the export: %s", media.id, str(error) or "its time ran out"
            )
            return None


def normalised(raw: bytes) -> Picture | None:
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(BytesIO(raw)) as opened:
            if opened.width * opened.height > PICTURE_MAX_PIXELS:
                return None
            image = opened.convert("RGBA")
    except UnidentifiedImageError, OSError, Image.DecompressionBombError:
        return None
    flat = Image.new("RGB", image.size, WHITE)
    flat.paste(image, mask=image.getchannel("A"))
    flat.thumbnail((PICTURE_MAX_SIDE, PICTURE_MAX_SIDE))
    out = BytesIO()
    flat.save(out, format="JPEG", quality=JPEG_QUALITY)
    return Picture(data=out.getvalue(), width=flat.width, height=flat.height)
