from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import INDIA_TZ
from app.models import FieldImage, MediaRef
from app.research.open_pictures import photo_credit
from app.research.page_layout import PageLayout, picture_label

from .field_photo_scope import shown_field_photos, shown_size
from .field_voices_image_store import IMAGE_ROUTE
from .monograph_generated_pictures import PlateSource
from .open_work_subjects import WorkSubject

__all__ = [
    "FIELD_KEY_PREFIX",
    "FIELD_PHOTOS_READ_MAX",
    "ClearedPhoto",
    "cleared_photos",
    "field_key",
    "field_plates",
    "placed_photo_labels",
]

FIELD_KEY_PREFIX = "field-"
FIELD_KEY_HEX_CHARS = 12
FIELD_PHOTOS_READ_MAX = 200
CRAFT = "craft"


@dataclass(frozen=True)
class ClearedPhoto:
    image_id: uuid.UUID
    key: str
    label: str
    src: str
    width: int
    height: int
    alt: str
    caption: str
    credit: str
    taken_on: date | None


def field_key(image_id: uuid.UUID) -> str:
    return f"{FIELD_KEY_PREFIX}{image_id.hex[:FIELD_KEY_HEX_CHARS]}"


async def cleared_photos(
    session: AsyncSession, subject: WorkSubject, *, limit: int = FIELD_PHOTOS_READ_MAX, offset: int = 0
) -> tuple[list[ClearedPhoto], int]:
    if subject.kind != CRAFT:
        return [], 0
    cleared = [*shown_field_photos(subject.id), FieldImage.artisanLinked.is_(False)]
    rows = await session.execute(
        select(FieldImage, MediaRef, *shown_size())
        .join(MediaRef, MediaRef.id == FieldImage.mediaRefId)
        .where(*cleared)
        .order_by(FieldImage.takenAt.desc().nulls_last(), FieldImage.id)
        .offset(offset)
        .limit(limit)
    )
    photos = [_cleared(subject, image, media, (width, height)) for image, media, width, height in rows]
    total = await session.scalar(select(func.count()).select_from(FieldImage).where(*cleared))
    return photos, int(total or 0)


def placed_photo_labels(subject: WorkSubject, layout: PageLayout | None) -> set[str]:
    if layout is None or subject.kind != CRAFT:
        return set()
    prefix = picture_label(subject.slug, FIELD_KEY_PREFIX.rstrip("-")) + "-"
    return {entry.ref for entry in layout.entries if entry.ref.startswith(prefix)}


async def field_plates(
    session: AsyncSession, subject: WorkSubject, layout: PageLayout | None
) -> list[PlateSource]:
    named = placed_photo_labels(subject, layout)
    if not named or layout is None:
        return []
    photos, _ = await cleared_photos(session, subject)
    return [_plate(photo, layout) for photo in photos if photo.label in named]


def _cleared(subject: WorkSubject, image: FieldImage, media: MediaRef, size: tuple[int, int]) -> ClearedPhoto:
    key = field_key(image.id)
    return ClearedPhoto(
        image_id=image.id,
        key=key,
        label=picture_label(subject.slug, key),
        src=IMAGE_ROUTE.format(id=image.id),
        width=size[0],
        height=size[1],
        alt=media.alt,
        caption=image.caption or media.title or media.alt,
        credit=photo_credit(media.author, None, media.site),
        taken_on=image.takenAt.astimezone(INDIA_TZ).date() if image.takenAt else None,
    )


def _plate(photo: ClearedPhoto, layout: PageLayout) -> PlateSource:
    entry = layout.entry(photo.label)
    if entry is None:
        raise ValueError(f"the layout names no {photo.label}")
    return PlateSource(
        key=photo.key,
        chapter=entry.chapter,
        role=entry.role,
        src=photo.src,
        width=photo.width,
        height=photo.height,
        alt=photo.alt,
        caption=photo.caption,
        credit=photo.credit,
        attribution=photo.credit,
    )
