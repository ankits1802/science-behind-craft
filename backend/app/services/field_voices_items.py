from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Self
from urllib.parse import parse_qsl, urlsplit

from pydantic import AwareDatetime, Field, model_validator

from app.services.field_voices_placements import refuse_identity_caption, refuse_never_image_field
from app.services.portal_craft_feed import FeedModel, Portal, refuse_duplicates

__all__ = [
    "IMAGE_EXTENSIONS",
    "IMAGE_KEY_PREFIX",
    "IMAGE_MAX_BYTES",
    "IMAGE_MAX_EDGE",
    "PERSON_KINDS",
    "PLACEMENT_KINDS",
    "SCRUB_LABELS",
    "SEGMENT_TEXT_MAX",
    "FeedArea",
    "FeedCraft",
    "FeedPerson",
    "FeedWorkshop",
    "ImageCredit",
    "ImageItem",
    "ImagePermission",
    "Placement",
    "RecordRef",
    "ScrubCount",
    "Scrubbing",
    "Segment",
    "SessionRef",
    "SignedImage",
    "Speaker",
    "StageRef",
    "Topic",
    "Transcript",
    "TranscriptItem",
]

PERSON_KINDS = ("ARTISAN", "DESIGNER", "RESEARCHER")
SPEAKER_ROLES = ("ARTISAN", "RESEARCHER", "OTHER")
CREDIT_ROLES = ("ARTISAN", "DESIGNER")
SCRUB_LABELS = ("EMAIL", "NUMBER", "PLACE")
TRANSCRIPT_SOURCES = ("TURNS", "TEXT", "TYPED")
TEXT_SOURCES = ("MACHINE", "EDITED", "TYPED")
ENGLISH_SOURCES = ("ORIGINAL", "MACHINE", "EDITED")
RECORD_KINDS = ("PRODUCT", "TOOL", "PROCESS", "PROCESS_STEP")
MEDIA_TYPES = ("AUDIO", "VIDEO")
WORKSHOP_KINDS = ("DESIGN_WORKSHOP", "WORKSHOP")
RECORD_PLACEMENTS = ("PRODUCT", "TOOL", "PROCESS", "PROCESS_STEP")
FILED_PLACEMENTS = ("ARTISAN", "DESIGNER", "SESSION", "WORKSHOP", "DESIGN_WORKSHOP")
PLACEMENT_KINDS = (*RECORD_PLACEMENTS, "CRAFT", "DESIGN_STAGE", *FILED_PLACEMENTS)
IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png"}
IMAGE_KEY_PREFIX = "field-voices"
IMAGE_MAX_EDGE = 2400
IMAGE_MAX_BYTES = 8 * 1024 * 1024
SEGMENT_TEXT_MAX = 20_000
YEARS_IN_CRAFT_MAX = 90
SIGNED_URL_MAX_CHARS = 4096
DISPOSITION_PARAM = "response-content-disposition"
LANGUAGE_PATTERN = r"^(?:und|[a-z]{2,3}(?:-[A-Za-z0-9]{1,8})*)$"
TOKEN_PATTERN = r"^\S+$"

Id = Annotated[str, Field(min_length=1, max_length=64, pattern=TOKEN_PATTERN)]
SegmentId = Annotated[str, Field(min_length=1, max_length=96, pattern=TOKEN_PATTERN)]
Label = Annotated[str, Field(min_length=1, max_length=600)]
Name = Annotated[str, Field(min_length=1, max_length=200)]
Language = Annotated[str, Field(pattern=LANGUAGE_PATTERN)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class FeedCraft(FeedModel):
    id: Id
    slug: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,199}$")
    code: str | None = Field(default=None, min_length=1, max_length=40)
    name: Name


class FeedArea(FeedModel):
    state: Name | None = None
    district: Name | None = None
    state_lgd: int | None = Field(default=None, ge=1)
    district_lgd: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _a_district_inside_a_state(self) -> Self:
        if self.district is not None and self.state is None:
            raise ValueError("an area names its state when it names a district")
        if (self.district is None) != (self.district_lgd is None):
            raise ValueError("a district comes with its LGD code")
        return self


class FeedWorkshop(FeedModel):
    kind: Literal[*WORKSHOP_KINDS]
    id: Id
    code: str | None = Field(default=None, min_length=1, max_length=40)
    title: Label | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    area: FeedArea | None = None

    @model_validator(mode="after")
    def _ends_after_it_starts(self) -> Self:
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError(f"workshop {self.id} ends before it starts")
        return self


class SamePerson(FeedModel):
    portal: Portal
    id: Id


class FeedPerson(FeedModel):
    id: Id
    kind: Literal[*PERSON_KINDS]
    name: Name | None = None
    local_name: Name | None = None
    years_in_craft: int | None = Field(default=None, ge=0, le=YEARS_IN_CRAFT_MAX)
    area: FeedArea | None = None
    same_person_in: tuple[SamePerson, ...] = ()
    merged_ids: tuple[Id, ...] = ()

    @model_validator(mode="after")
    def _artisan_fields_only_for_artisans(self) -> Self:
        artisan_only = (self.years_in_craft, self.area, self.same_person_in or None, self.merged_ids or None)
        if self.kind != "ARTISAN" and any(value is not None for value in artisan_only):
            raise ValueError(f"person {self.id} is not an artisan and carries an artisan's fields")
        return self


class ScrubCount(FeedModel):
    kind: Literal[*SCRUB_LABELS]
    count: int = Field(ge=0)


class Scrubbing(FeedModel):
    version: int = Field(ge=1)
    replaced: tuple[ScrubCount, ...]
    nulled: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _each_kind_counted_once(self) -> Self:
        refuse_duplicates("scrub kind", [entry.kind for entry in self.replaced])
        return self


class QuestionnaireRef(FeedModel):
    id: Id
    title: Label | None = None


class SessionRef(FeedModel):
    id: Id
    title: Label | None = None
    held_on: date | None = Field(default=None, alias="date")
    purpose: str | None = Field(default=None, min_length=1, max_length=40)
    questionnaire: QuestionnaireRef | None = None


class Topic(FeedModel):
    section_id: Id | None = None
    section_code: str | None = Field(default=None, min_length=1, max_length=40)
    section_title: Label | None = None
    question_id: Id | None = None
    question_code: str | None = Field(default=None, min_length=1, max_length=40)
    question: str | None = Field(default=None, min_length=1, max_length=2000)


class StageRef(FeedModel):
    key: str = Field(min_length=1, max_length=60)
    title: Label
    entity: str = Field(min_length=1, max_length=60)
    entity_label: Label
    row_id: Id
    row_label: Label | None = None
    field: str = Field(min_length=1, max_length=60)
    field_label: Label


class RecordRef(FeedModel):
    kind: Literal[*RECORD_KINDS]
    id: Id
    name: Label | None = None
    local_name: Label | None = None


class Speaker(FeedModel):
    key: str = Field(min_length=1, max_length=40)
    label: Label
    role: Literal[*SPEAKER_ROLES] | None = None
    person_id: Id | None = None


class Segment(FeedModel):
    id: SegmentId
    position: int = Field(ge=0)
    speaker_key: str | None = Field(default=None, min_length=1, max_length=40)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=1)
    language: Language
    text: str = Field(min_length=1, max_length=SEGMENT_TEXT_MAX)
    text_source: Literal[*TEXT_SOURCES]
    english: str | None = Field(default=None, min_length=1, max_length=SEGMENT_TEXT_MAX * 2)
    english_source: Literal[*ENGLISH_SOURCES] | None = None
    scrubbed: tuple[Literal[*SCRUB_LABELS], ...] = ()

    @model_validator(mode="after")
    def _timed_and_translated_together(self) -> Self:
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError(f"segment {self.id} is timed at both ends or untimed")
        if self.start_ms is not None and self.end_ms is not None and self.end_ms <= self.start_ms:
            raise ValueError(f"segment {self.id} ends before it starts")
        if (self.english is None) != (self.english_source is None):
            raise ValueError(f"segment {self.id}: english and englishSource come together")
        return self


class EnglishText(FeedModel):
    text: str = Field(min_length=1, max_length=SEGMENT_TEXT_MAX * 20)
    source: Literal["MACHINE", "EDITED"]


class Transcript(FeedModel):
    source: Literal[*TRANSCRIPT_SOURCES]
    version: int | None = Field(default=None, ge=1)
    languages: tuple[Language, ...] = Field(min_length=1)
    detected_language: Language | None = None
    segments: tuple[Segment, ...] = Field(min_length=1)
    english: EnglishText | None = None

    @model_validator(mode="after")
    def _segments_in_order(self) -> Self:
        refuse_duplicates("segment", [segment.id for segment in self.segments])
        positions = [segment.position for segment in self.segments]
        if positions != sorted(set(positions)):
            raise ValueError("segments are listed once each in position order")
        if (self.version is not None) != (self.source == "TURNS"):
            raise ValueError("a transcript version is sent for TURNS only")
        if self.english is not None and self.source != "TEXT":
            raise ValueError("a whole-transcript English is sent for TEXT only")
        if self.source != "TURNS" and any(segment.start_ms is not None for segment in self.segments):
            raise ValueError(f"a {self.source} transcript is untimed")
        return self


class TranscriptItem(FeedModel):
    id: Id
    recording_id: Id | None = None
    media_type: Literal[*MEDIA_TYPES]
    recorded_at: AwareDatetime
    duration_ms: int | None = Field(default=None, ge=1)
    crafts: tuple[FeedCraft, ...] = Field(min_length=1)
    workshop: FeedWorkshop | None = None
    session: SessionRef | None = None
    topics: tuple[Topic, ...] = ()
    stage: StageRef | None = None
    record: RecordRef | None = None
    area: FeedArea | None = None
    people: tuple[FeedPerson, ...] = ()
    speakers: tuple[Speaker, ...] = ()
    transcript: Transcript
    scrubbing: Scrubbing

    @model_validator(mode="after")
    def _everything_resolves_inside_the_item(self) -> Self:
        refuse_duplicates(f"recording {self.id} person", [person.id for person in self.people])
        refuse_duplicates(f"recording {self.id} speaker", [speaker.key for speaker in self.speakers])
        refuse_duplicates(f"recording {self.id} craft", [craft.id for craft in self.crafts])
        people = {person.id for person in self.people}
        if any(s.person_id is not None and s.person_id not in people for s in self.speakers):
            raise ValueError(f"recording {self.id} maps a speaker to a person it does not list")
        keys = {speaker.key for speaker in self.speakers}
        if any(s.speaker_key is not None and s.speaker_key not in keys for s in self.transcript.segments):
            raise ValueError(f"recording {self.id} has a segment of a speaker it does not list")
        if self.transcript.source == "TYPED" and self.speakers:
            raise ValueError(f"recording {self.id} is a typed transcript and names speakers")
        if self.duration_ms and any((s.end_ms or 0) > self.duration_ms for s in self.transcript.segments):
            raise ValueError(f"recording {self.id} has a segment past its end")
        return self


class StageName(FeedModel):
    key: str = Field(min_length=1, max_length=60)
    title: Label


class EntityName(FeedModel):
    key: str = Field(min_length=1, max_length=60)
    label: Label


class RowName(FeedModel):
    id: Id
    label: Label | None = None


class FieldName(FeedModel):
    key: str = Field(min_length=1, max_length=60)
    label: Label


class Placement(FeedModel):
    kind: Literal[*PLACEMENT_KINDS]
    id: Id | None = None
    name: Label | None = None
    local_name: Label | None = None
    english_name: Label | None = None
    product_type: str | None = Field(default=None, min_length=1, max_length=40)
    product_id: Id | None = None
    process_id: Id | None = None
    process: Label | None = None
    order: int | None = Field(default=None, ge=0)
    stage: StageName | None = None
    entity: EntityName | None = None
    row: RowName | None = None
    field: FieldName | None = None
    prototype_id: Id | None = None

    @model_validator(mode="after")
    def _kind_names_what_it_needs(self) -> Self:
        if self.kind == "DESIGN_STAGE":
            if self.stage is None or self.entity is None or self.row is None or self.field is None:
                raise ValueError("a design stage placement names its stage, entity, row and field")
            refuse_never_image_field(self.stage.key, self.entity.key, self.field.key)
        elif self.kind != "CRAFT" and self.id is None:
            raise ValueError(f"a {self.kind} placement names its record")
        return self


class ImageCredit(FeedModel):
    person_id: Id
    role: Literal[*CREDIT_ROLES] = Field(alias="as")


class ImagePermission(FeedModel):
    statement: str = Field(min_length=1, max_length=600)
    rights_holder: Name
    licence: str | None = Field(default=None, min_length=1, max_length=200)


class SignedImage(FeedModel):
    url: str = Field(max_length=SIGNED_URL_MAX_CHARS, pattern=r"^https://\S+$")
    expires_at: AwareDatetime
    mime_type: Literal[*IMAGE_EXTENSIONS]
    width: int = Field(ge=1, le=IMAGE_MAX_EDGE)
    height: int = Field(ge=1, le=IMAGE_MAX_EDGE)
    bytes: int = Field(ge=1, le=IMAGE_MAX_BYTES)
    sha256: Sha256

    @property
    def leaf(self) -> str:
        return f"{self.sha256}.{IMAGE_EXTENSIONS[self.mime_type]}"

    @model_validator(mode="after")
    def _names_only_the_neutral_copy(self) -> Self:
        parts = urlsplit(self.url)
        if (
            not parts.hostname
            or parts.username
            or parts.port
            or parts.path != f"/{IMAGE_KEY_PREFIX}/{self.leaf}"
        ):
            raise ValueError(f"image url must name the copy /{IMAGE_KEY_PREFIX}/{self.leaf} and nothing else")
        for key, value in parse_qsl(parts.query):
            if key.lower() == DISPOSITION_PARAM and "filename" in value.lower() and self.leaf not in value:
                raise ValueError("image url names a file other than its copy")
        return self


class ImageItem(FeedModel):
    id: Id
    taken_at: AwareDatetime | None = None
    caption: Label | None = None
    artisan_linked: bool
    crafts: tuple[FeedCraft, ...] = Field(min_length=1)
    belongs_to: tuple[Placement, ...] = Field(min_length=1)
    workshop: FeedWorkshop | None = None
    people: tuple[FeedPerson, ...] = ()
    credits: tuple[ImageCredit, ...] = ()
    permission: ImagePermission
    image: SignedImage
    scrubbing: Scrubbing

    @model_validator(mode="after")
    def _credits_name_listed_people(self) -> Self:
        refuse_identity_caption(self.id, self.caption)
        refuse_duplicates(f"image {self.id} person", [person.id for person in self.people])
        refuse_duplicates(f"image {self.id} craft", [craft.id for craft in self.crafts])
        people = {person.id for person in self.people}
        if any(credit.person_id not in people for credit in self.credits):
            raise ValueError(f"image {self.id} credits a person it does not list")
        return self
