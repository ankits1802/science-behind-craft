from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import date
from types import MappingProxyType
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import ENGLISH_SOURCES

from .base import ContractModel, HttpsUrl
from .crafts import CraftRef
from .voices import VoiceQuote

__all__ = [
    "ARTISAN_IMAGES_HIDDEN",
    "ARTISAN_IMAGES_SETTING",
    "ARTISAN_IMAGES_SHOWN",
    "ARTISAN_IMAGE_VISIBILITIES",
    "FIELD_EVIDENCE_KIND",
    "FIELD_IMAGE_PROVIDERS",
    "FIELD_LIST_KINDS",
    "FIELD_LIST_PAGE_SIZE",
    "FIELD_LIST_SCHEMA_VERSION",
    "FIELD_PHOTOS_SHOWN",
    "FIELD_SOURCE_KIND",
    "FIELD_TRANSCRIPT_SCHEMA_VERSION",
    "FIELD_VOICES_ADAPTER",
    "FIELD_VOICES_SHOWN",
    "PHOTO_GROUP_KINDS",
    "PORTAL_EXTERNAL_KEYS",
    "PORTAL_PROVIDERS",
    "PORTAL_PUBLISHERS",
    "FieldTranscript",
    "FieldVoicesList",
    "FieldVoicesTotals",
    "HeldImage",
    "HeldImageList",
    "PageFieldPhoto",
    "PageVoice",
    "PhotoGroup",
    "TranscriptLine",
    "TranscriptSpeaker",
    "VoiceStage",
]

FIELD_SOURCE_KIND = "FIELD_TESTIMONY"
FIELD_EVIDENCE_KIND = "FIELD_INTERVIEW"
FIELD_VOICES_ADAPTER = "field_voices"
PORTAL_PUBLISHERS: Mapping[str, str] = MappingProxyType(
    {"DESIGNER": "DesignWorkshop", "FIELD_REPOSITORY": "Field Repository"}
)
PORTAL_PROVIDERS: Mapping[str, str] = MappingProxyType(
    {"DESIGNER": "designer_portal", "FIELD_REPOSITORY": "field_repository"}
)
PORTAL_EXTERNAL_KEYS: Mapping[str, str] = MappingProxyType(
    {"DESIGNER": "designerPortal", "FIELD_REPOSITORY": "fieldRepository"}
)
FIELD_IMAGE_PROVIDERS = frozenset(PORTAL_PROVIDERS.values())
FIELD_ORIGINS = ("DESIGNER", "FIELD_REPOSITORY")
LINE_ROLES = ("ARTISAN", "DESIGNER", "RESEARCHER", "OTHER")
STAGE_LINK_KINDS = ("DESIGN_STAGE", "QUESTION", "RECORD")
ARTISAN_IMAGES_SETTING = "field_voices.artisan_images"
ARTISAN_IMAGES_HIDDEN = "HIDDEN"
ARTISAN_IMAGES_SHOWN = "SHOWN"
ARTISAN_IMAGE_VISIBILITIES = (ARTISAN_IMAGES_HIDDEN, ARTISAN_IMAGES_SHOWN)
HELD_IMAGES_SCHEMA_VERSION = 1
PHOTO_GROUP_KINDS = (
    "PRODUCT",
    "TOOL",
    "PROCESS",
    "PROCESS_STEP",
    "PROTOTYPE",
    "DESIGN_STAGE",
    "CRAFT",
    "PERSON",
    "SESSION",
    "WORKSHOP",
)
FIELD_LIST_KINDS = ("quotes", "images")
FIELD_VOICES_SHOWN = 6
FIELD_PHOTOS_SHOWN = 12
FIELD_LIST_PAGE_SIZE = 25
FIELD_LIST_SCHEMA_VERSION = 1
FIELD_TRANSCRIPT_SCHEMA_VERSION = 1

Line = str


class VoiceStage(ContractModel):
    kind: Literal[*STAGE_LINK_KINDS]
    key: str | None = Field(max_length=60)
    label: Line = Field(min_length=1, max_length=600)


class PageVoice(VoiceQuote):
    stage: VoiceStage | None = None
    citation: Line = Field(min_length=1, max_length=600)
    recording_id: uuid.UUID | None = None


class PhotoGroup(ContractModel):
    kind: Literal[*PHOTO_GROUP_KINDS]
    key: str = Field(min_length=1, max_length=120)
    label: Line = Field(min_length=1, max_length=600)


class PageFieldPhoto(ContractModel):
    item_id: str = Field(min_length=3, max_length=200)
    origin: Literal[*FIELD_ORIGINS]
    image_url: HttpsUrl
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    caption: str | None = Field(min_length=1)
    alt: str = Field(min_length=1, max_length=300)
    credit: Line = Field(min_length=1, max_length=600)
    credited: list[str]
    workshop: str | None = Field(min_length=1, max_length=400)
    taken_on: date | None
    groups: list[PhotoGroup] = Field(min_length=1)
    statement: str = Field(min_length=1, max_length=600)
    rights_holder: str = Field(min_length=1, max_length=200)
    licence: None


class FieldVoicesTotals(ContractModel):
    quotes: int = Field(ge=0)
    images: int = Field(ge=0)


class FieldVoicesList(ContractModel):
    schema_version: Literal[1]
    craft: CraftRef
    kind: Literal[*FIELD_LIST_KINDS]
    total: int = Field(ge=0)
    cursor: str | None
    next_cursor: str | None
    quotes: list[PageVoice]
    images: list[PageFieldPhoto]

    @model_validator(mode="after")
    def _one_kind_per_list(self) -> Self:
        other = self.images if self.kind == "quotes" else self.quotes
        if other:
            raise ValueError(f"a {self.kind} list carries only {self.kind}")
        if len(self.quotes) + len(self.images) > FIELD_LIST_PAGE_SIZE:
            raise ValueError(f"a list page holds at most {FIELD_LIST_PAGE_SIZE} items")
        return self


class TranscriptSpeaker(ContractModel):
    key: str = Field(min_length=1, max_length=40)
    label: Line = Field(min_length=1, max_length=400)
    role: Literal[*LINE_ROLES] | None


class TranscriptLine(ContractModel):
    id: str = Field(min_length=1, max_length=96)
    position: int = Field(ge=0)
    speaker_key: str | None
    locator: str = Field(min_length=1, max_length=40)
    language: str = Field(min_length=2, max_length=16)
    text: str = Field(min_length=1)
    english: str | None = Field(min_length=1)
    english_source: Literal[*ENGLISH_SOURCES] | None
    quotable: bool


class FieldTranscript(ContractModel):
    schema_version: Literal[1]
    id: uuid.UUID
    origin: Literal[*FIELD_ORIGINS]
    publisher: str = Field(min_length=1)
    title: Line = Field(min_length=1)
    media_type: Literal["AUDIO", "VIDEO"]
    recorded_at: AwareDatetime
    duration_ms: int | None = Field(ge=1)
    crafts: list[CraftRef]
    workshop: str | None = Field(min_length=1, max_length=400)
    context: list[Line]
    stage: VoiceStage | None
    speakers: list[TranscriptSpeaker]
    lines: list[TranscriptLine] = Field(min_length=1)
    english: str | None = Field(min_length=1)
    english_source: Literal["MACHINE", "EDITED"] | None
    source_id: uuid.UUID
    citation: Line = Field(min_length=1)

    @model_validator(mode="after")
    def _lines_name_listed_speakers(self) -> Self:
        keys = {speaker.key for speaker in self.speakers}
        if any(line.speaker_key is not None and line.speaker_key not in keys for line in self.lines):
            raise ValueError(f"transcript {self.id} has a line of a speaker it does not list")
        return self


class HeldImage(ContractModel):
    id: uuid.UUID
    item_id: str = Field(min_length=3, max_length=200)
    origin: Literal[*FIELD_ORIGINS]
    caption: str | None = Field(min_length=1)
    taken_on: date | None
    crafts: list[str]
    placements: list[str]
    credited: list[str]
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class HeldImageList(ContractModel):
    schema_version: Literal[1]
    visibility: Literal[*ARTISAN_IMAGE_VISIBILITIES]
    total: int = Field(ge=0)
    cursor: str | None
    next_cursor: str | None
    images: list[HeldImage] = Field(max_length=FIELD_LIST_PAGE_SIZE)
