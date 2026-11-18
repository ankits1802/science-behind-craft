from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import ColumnElement, Select, and_, exists, func, literal, not_, or_, select
from sqlalchemy.dialects.postgresql import JSONB

from app.models import (
    AppSetting,
    FieldImage,
    FieldImageCraft,
    FieldRecording,
    FieldRecordingCraft,
    FieldVoiceStream,
)
from app.research.field_voices import ARTISAN_IMAGES_SETTING, ARTISAN_IMAGES_SHOWN

__all__ = [
    "FIELD_STALE_AFTER",
    "artisan_images_shown",
    "field_interview_sources",
    "fresh_portals",
    "held_images",
    "shown_images",
    "shown_recordings",
    "withheld_field_sources",
]

FIELD_STALE_AFTER = timedelta(days=7)
TRANSCRIPTS = "TRANSCRIPTS"
IMAGES = "IMAGES"


def fresh_portals(stream: str) -> Select[tuple[str]]:
    return select(FieldVoiceStream.portal).where(
        FieldVoiceStream.stream == stream, FieldVoiceStream.lastContactAt >= func.now() - FIELD_STALE_AFTER
    )


def shown_recordings(craft_id: uuid.UUID | None = None) -> list[ColumnElement[bool]]:
    linked = select(FieldRecordingCraft.recordingId)
    if craft_id is not None:
        linked = linked.where(FieldRecordingCraft.craftId == craft_id)
    return [
        FieldRecording.hiddenAt.is_(None),
        FieldRecording.portal.in_(fresh_portals(TRANSCRIPTS)),
        FieldRecording.id.in_(linked),
    ]


def artisan_images_shown() -> ColumnElement[bool]:
    return exists(
        select(AppSetting.id).where(
            AppSetting.key == ARTISAN_IMAGES_SETTING,
            AppSetting.value == literal(ARTISAN_IMAGES_SHOWN, JSONB),
        )
    )


def shown_images(craft_id: uuid.UUID | None = None) -> list[ColumnElement[bool]]:
    linked = select(FieldImageCraft.imageId)
    if craft_id is not None:
        linked = linked.where(FieldImageCraft.craftId == craft_id)
    return [
        FieldImage.hiddenAt.is_(None),
        or_(FieldImage.artisanLinked.is_(False), artisan_images_shown()),
        FieldImage.portal.in_(fresh_portals(IMAGES)),
        FieldImage.id.in_(linked),
    ]


def held_images() -> list[ColumnElement[bool]]:
    return [FieldImage.hiddenAt.is_(None), FieldImage.artisanLinked.is_(True)]


def field_interview_sources(craft_id: uuid.UUID | None = None) -> Select[tuple[uuid.UUID]]:
    return select(FieldRecording.sourceId).where(*shown_recordings(craft_id))


def withheld_field_sources() -> Select[tuple[uuid.UUID]]:
    return select(FieldRecording.sourceId).where(not_(and_(*shown_recordings()))).correlate(None)
