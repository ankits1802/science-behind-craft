from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urlsplit

import httpx

from app.core.errors import ExternalFailure, InvalidInput
from app.services.field_voices_items import FeedArea, ImageItem, SignedImage
from app.services.malware_scan import scanned_upload
from app.services.naming import PlaceParts, field_voice_file_name, field_voice_key
from app.services.object_store import ObjectStore

__all__ = ["DOWNLOAD_TIMEOUT_SECONDS", "ImageCopier", "NeutralCopy", "StoredCopy", "neutral_copy"]

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT_SECONDS = 30.0
MAX_PIXELS = 60_000_000
JPEG_QUALITY = 90
FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG"}
EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png"}
TRANSPARENT_MODES = ("RGBA", "LA", "PA")
SERVICE = "field_voices_images"


@dataclass(frozen=True)
class StoredCopy:
    key: str
    mime_type: str
    width: int
    height: int
    bytes: int
    sha256: str
    portal_sha256: str


@dataclass(frozen=True)
class NeutralCopy:
    data: bytes
    mime_type: str
    width: int
    height: int


class ImageCopier:
    def __init__(
        self,
        store: ObjectStore,
        *,
        image_hosts: frozenset[str],
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._store = store
        self._image_hosts = image_hosts
        self._transport = transport

    async def copy(self, item: ImageItem) -> StoredCopy:
        raw = await self._download(item.image)
        await scanned_upload(raw)
        made = await asyncio.to_thread(neutral_copy, raw, item.image)
        sha = hashlib.sha256(made.data).hexdigest()
        leaf = field_voice_file_name(
            taken_at=item.taken_at,
            place=_place(item),
            craft=item.crafts[0].name,
            ext=EXTENSIONS[made.mime_type],
        )
        key = field_voice_key(sha, leaf)
        if not await self._store.exists(key):
            await self._store.put(key, made.data, content_type=made.mime_type)
        return StoredCopy(
            key=key,
            mime_type=made.mime_type,
            width=made.width,
            height=made.height,
            bytes=len(made.data),
            sha256=sha,
            portal_sha256=item.image.sha256,
        )

    async def _download(self, image: SignedImage) -> bytes:
        host = (urlsplit(image.url).hostname or "").lower()
        if host not in self._image_hosts:
            raise InvalidInput(f"image {image.sha256} is not on a listed image host")
        try:
            async with httpx.AsyncClient(
                timeout=DOWNLOAD_TIMEOUT_SECONDS, transport=self._transport, follow_redirects=False
            ) as client:
                response = await client.get(image.url)
        except httpx.HTTPError as error:
            raise ExternalFailure(
                f"image {image.sha256} could not be downloaded ({type(error).__name__})",
                kind="unavailable",
                retryable=True,
                service=SERVICE,
            ) from None
        if response.status_code != 200:
            raise ExternalFailure(
                f"image {image.sha256} answered {response.status_code}",
                status=response.status_code,
                service=SERVICE,
            )
        return _verified(response.content, image)


def neutral_copy(raw: bytes, image: SignedImage) -> NeutralCopy:
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with Image.open(BytesIO(raw)) as opened:
            if opened.width * opened.height > MAX_PIXELS:
                raise InvalidInput(f"image {image.sha256} is over {MAX_PIXELS} pixels")
            if opened.format != FORMATS[image.mime_type] or opened.size != (image.width, image.height):
                raise InvalidInput(f"image {image.sha256} is not the {image.mime_type} it was sent as")
            upright = ImageOps.exif_transpose(opened)
            transparent = upright.mode in TRANSPARENT_MODES or "transparency" in upright.info
            clean = upright.convert("RGBA" if transparent else "RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise InvalidInput(f"image {image.sha256} cannot be decoded ({type(error).__name__})") from None
    clean.info = {}
    out = BytesIO()
    mime = "image/png" if transparent else "image/jpeg"
    if transparent:
        clean.save(out, format="PNG", optimize=True)
    else:
        clean.save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return NeutralCopy(data=out.getvalue(), mime_type=mime, width=clean.width, height=clean.height)


def _verified(body: bytes, image: SignedImage) -> bytes:
    if len(body) != image.bytes:
        raise InvalidInput(f"image {image.sha256} is {len(body)} bytes, not the {image.bytes} sent")
    if hashlib.sha256(body).hexdigest() != image.sha256:
        raise InvalidInput(f"image {image.sha256} does not match its SHA-256")
    return body


def _place(item: ImageItem) -> PlaceParts:
    areas: list[FeedArea | None] = [item.workshop.area if item.workshop else None]
    areas += [person.area for person in item.people]
    area = next((each for each in areas if each is not None), None)
    return PlaceParts(district=area.district, state=area.state) if area else PlaceParts()
