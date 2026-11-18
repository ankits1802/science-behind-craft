from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Annotated, Any, Literal, Self
from urllib.parse import parse_qsl, urlsplit

from pydantic import AwareDatetime, Field, ValidationError, model_validator

from app.core.errors import InvalidInput
from app.services.field_voices_never_sent import forbidden_keys
from app.services.portal_craft_feed import FeedModel, Portal, first_problem, refuse_duplicates

__all__ = [
    "CONSENT_BASES",
    "FIELD_VOICES_SCHEMA_VERSION",
    "IMAGE_KEY_PREFIX",
    "IMAGE_MAX_EDGE",
    "SIGNED_URL_MAX_LIFE",
    "ArtisanCredit",
    "Consent",
    "FieldPhotograph",
    "FieldQuote",
    "FieldRecording",
    "FieldVoicesEntry",
    "FieldVoicesIndex",
    "Permission",
    "PhotographsPage",
    "QuotesPage",
    "SignedImage",
    "Stage",
    "Topic",
    "VoicesPage",
    "Workshop",
    "parse_index",
    "parse_photographs_page",
    "parse_quotes_page",
    "snapshot_digest",
]

FIELD_VOICES_SCHEMA_VERSION = 1
CONSENT_BASES = ("VERBAL_RECORDED", "VERBAL_WITNESSED", "SIGNED_FORM", "OWNER_ATTESTATION")
OWNER_ATTESTATION = "OWNER_ATTESTATION"
CONSENT_SCOPES = ("RECORDING", "ARTISAN")
RECORDING_SCOPE = "RECORDING"
TEXT_SOURCES = ("MACHINE", "EDITED")
ENGLISH_SOURCES = ("ORIGINAL", "MACHINE", "EDITED")
IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
IMAGE_TYPES = tuple(IMAGE_EXTENSIONS)
IMAGE_KEY_PREFIX = "field-voices"
DISPOSITION_PARAM = "response-content-disposition"
DISPOSITION_FILE_NAMES = re.compile(r"filename\*?=(?:UTF-8'')?\"?([^\";]*)\"?", re.IGNORECASE)
QUOTE_MAX_CHARS = 4000
ENGLISH_MAX_CHARS = 8000
IMAGE_MAX_EDGE = 2400
IMAGE_MAX_BYTES = 8 * 1024 * 1024
SIGNED_URL_MAX_CHARS = 4096
SIGNED_URL_MAX_LIFE = timedelta(minutes=15)
CLOCK_SKEW = timedelta(minutes=2)
YEARS_IN_CRAFT_MAX = 90
LANGUAGE_PATTERN = r"^(?:und|[a-z]{2,3}(?:-[A-Za-z0-9]{1,8})*)$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
SLUG_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9-]{0,199}$"
SIGNED_URL_PATTERN = r"^https://\S+$"
TOKEN_PATTERN = r"^\S+$"


Id = Annotated[str, Field(min_length=1, max_length=64, pattern=TOKEN_PATTERN)]
Revision = Annotated[str, Field(min_length=1, max_length=64, pattern=TOKEN_PATTERN)]
Place = Annotated[str, Field(min_length=1, max_length=120)]
Sha256 = Annotated[str, Field(pattern=SHA256_PATTERN)]
CraftSlug = Annotated[str, Field(pattern=SLUG_PATTERN)]
Cursor = Annotated[str, Field(min_length=1, max_length=512)]
Language = Annotated[str, Field(pattern=LANGUAGE_PATTERN)]


class Consent(FeedModel):
    basis: Literal[*CONSENT_BASES]
    scope: Literal[*CONSENT_SCOPES]
    recorded_at: AwareDatetime


class ArtisanCredit(FeedModel):
    id: Id
    named: bool
    name: str | None = Field(default=None, min_length=1, max_length=200)
    local_name: str | None = Field(default=None, min_length=1, max_length=200)
    years_in_craft: int | None = Field(default=None, ge=0, le=YEARS_IN_CRAFT_MAX)
    district: Place | None = None
    state: Place | None = None
    consent: Consent

    @model_validator(mode="after")
    def _named_means_a_name(self) -> Self:
        if self.named != (self.name is not None):
            raise ValueError(f"artisan {self.id}: a name is sent exactly when named is true")
        if not self.named and self.local_name is not None:
            raise ValueError(f"artisan {self.id} is unnamed and carries a local name")
        return self


class Workshop(FeedModel):
    id: Id
    title: str | None = Field(default=None, min_length=1, max_length=300)
    starts_on: date | None = None
    ends_on: date | None = None
    district: Place | None = None
    state: Place | None = None

    @model_validator(mode="after")
    def _ends_after_start(self) -> Self:
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError(f"workshop {self.id} ends before it starts")
        return self


class Topic(FeedModel):
    section_code: str = Field(min_length=1, max_length=40)
    section_title: str = Field(min_length=1, max_length=200)
    question: str | None = Field(default=None, min_length=1, max_length=1000)


class FieldQuote(FeedModel):
    id: str = Field(min_length=1, max_length=80, pattern=TOKEN_PATTERN)
    artisan_id: Id
    position: int = Field(ge=0)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=1)
    language: Language
    text: str = Field(min_length=1, max_length=QUOTE_MAX_CHARS)
    text_source: Literal[*TEXT_SOURCES]
    english: str | None = Field(default=None, min_length=1, max_length=ENGLISH_MAX_CHARS)
    english_source: Literal[*ENGLISH_SOURCES] | None = None

    @model_validator(mode="after")
    def _timed_and_translated_together(self) -> Self:
        if self.end_ms <= self.start_ms:
            raise ValueError(f"quote {self.id} ends before it starts")
        if (self.english is None) != (self.english_source is None):
            raise ValueError(f"quote {self.id}: english and englishSource come together")
        return self


class FieldRecording(FeedModel):
    id: Id
    media_id: Id
    revision: Revision
    recorded_at: AwareDatetime
    duration_ms: int | None = Field(default=None, ge=1)
    workshop: Workshop | None = None
    topics: tuple[Topic, ...] = ()
    artisans: tuple[ArtisanCredit, ...] = Field(min_length=1)
    quotes: tuple[FieldQuote, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _quotes_belong_to_credited_speakers(self) -> Self:
        refuse_duplicates(f"recording {self.id} artisan", [a.id for a in self.artisans])
        refuse_duplicates(f"recording {self.id} quote", [q.id for q in self.quotes])
        credited = {a.id for a in self.artisans}
        speakers = {q.artisan_id for q in self.quotes}
        if speakers - credited:
            raise ValueError(f"recording {self.id} quotes an artisan it does not credit")
        if credited - speakers:
            raise ValueError(f"recording {self.id} credits an artisan who is not quoted")
        if self.duration_ms and any(q.end_ms > self.duration_ms for q in self.quotes):
            raise ValueError(f"recording {self.id} has a quote past its end")
        return self


class Stage(FeedModel):
    process: str = Field(min_length=1, max_length=200)
    step: str = Field(min_length=1, max_length=200)
    step_order: int | None = Field(default=None, ge=0)


class SignedImage(FeedModel):
    url: str = Field(max_length=SIGNED_URL_MAX_CHARS, pattern=SIGNED_URL_PATTERN)
    expires_at: AwareDatetime
    mime_type: Literal[*IMAGE_TYPES]
    width: int = Field(ge=1, le=IMAGE_MAX_EDGE)
    height: int = Field(ge=1, le=IMAGE_MAX_EDGE)
    bytes: int = Field(ge=1, le=IMAGE_MAX_BYTES)
    sha256: Sha256

    @model_validator(mode="after")
    def _names_only_the_opaque_copy(self) -> Self:
        leaf = f"{self.sha256}.{IMAGE_EXTENSIONS[self.mime_type]}"
        parts = urlsplit(self.url)
        if not parts.hostname or parts.username or parts.port or parts.path != f"/{IMAGE_KEY_PREFIX}/{leaf}":
            raise ValueError(f"image url must name the copy /{IMAGE_KEY_PREFIX}/{leaf} and nothing else")
        named = [
            name
            for key, value in parse_qsl(parts.query)
            if key.lower() == DISPOSITION_PARAM
            for name in DISPOSITION_FILE_NAMES.findall(value)
        ]
        if any(name != leaf for name in named):
            raise ValueError("image url names a file other than its copy")
        return self


class Permission(FeedModel):
    statement: str = Field(min_length=1, max_length=600)
    rights_holder: str = Field(min_length=1, max_length=200)
    licence: str | None = Field(default=None, min_length=1, max_length=200)


class FieldPhotograph(FeedModel):
    id: Id
    revision: Revision
    taken_at: AwareDatetime | None = None
    caption: str | None = Field(default=None, min_length=1, max_length=600)
    stage: Stage | None = None
    workshop: Workshop | None = None
    artisans: tuple[ArtisanCredit, ...] = ()
    consent: Consent
    permission: Permission
    image: SignedImage

    @model_validator(mode="after")
    def _consented_for_this_picture(self) -> Self:
        if self.consent.scope != RECORDING_SCOPE or self.consent.basis == OWNER_ATTESTATION:
            raise ValueError(f"photograph {self.id} needs its own consent, recorded by a person")
        refuse_duplicates(f"photograph {self.id} artisan", [a.id for a in self.artisans])
        return self


class FieldVoicesEntry(FeedModel):
    craft_slug: CraftSlug
    craft_code: str | None = Field(default=None, min_length=1, max_length=40)
    recordings: int = Field(ge=0)
    quotes: int = Field(ge=0)
    photographs: int = Field(ge=0)
    digest: Sha256
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def _lists_something(self) -> Self:
        if self.recordings + self.photographs == 0:
            raise ValueError(f"craft {self.craft_slug} is listed with nothing to publish")
        if self.quotes < self.recordings:
            raise ValueError(f"craft {self.craft_slug} has fewer quotes than recordings")
        return self


class FieldVoicesIndex(FeedModel):
    schema_version: Literal[1]
    portal: Portal
    generated_at: AwareDatetime
    crafts: tuple[FieldVoicesEntry, ...]

    @model_validator(mode="after")
    def _one_entry_per_craft(self) -> Self:
        refuse_duplicates("craft", [c.craft_slug for c in self.crafts])
        return self


class VoicesPage(FeedModel):
    schema_version: Literal[1]
    portal: Portal
    generated_at: AwareDatetime
    craft_slug: CraftSlug
    cursor: Cursor | None = None
    next_cursor: Cursor | None = None


class QuotesPage(VoicesPage):
    recordings: tuple[FieldRecording, ...]


class PhotographsPage(VoicesPage):
    photographs: tuple[FieldPhotograph, ...]

    @model_validator(mode="after")
    def _urls_are_short_lived(self) -> Self:
        latest = self.generated_at + SIGNED_URL_MAX_LIFE + CLOCK_SKEW
        for photograph in self.photographs:
            if not self.generated_at < photograph.image.expires_at <= latest:
                raise ValueError(
                    f"photograph {photograph.id} has a signed URL outside the 15 minutes allowed"
                )
        return self


def parse_index(payload: Any, *, portal: str) -> FieldVoicesIndex:
    return _validated(FieldVoicesIndex, payload, portal=portal, what="field voices index")


def parse_quotes_page(payload: Any, *, portal: str, craft_slug: str, cursor: str | None) -> QuotesPage:
    page = _validated(QuotesPage, payload, portal=portal, what=f"{craft_slug} quotes page")
    _refuse_other_request(page, craft_slug, cursor)
    return page


def parse_photographs_page(
    payload: Any, *, portal: str, craft_slug: str, cursor: str | None, image_hosts: frozenset[str]
) -> PhotographsPage:
    page = _validated(PhotographsPage, payload, portal=portal, what=f"{craft_slug} photographs page")
    _refuse_other_request(page, craft_slug, cursor)
    _refuse_other_image_hosts(page, image_hosts)
    return page


def snapshot_digest(recordings: Iterable[FieldRecording], photographs: Iterable[FieldPhotograph]) -> str:
    lines = [f"R {r.id} {r.revision}\n" for r in recordings]
    lines += [f"P {p.id} {p.revision}\n" for p in photographs]
    return hashlib.sha256("".join(sorted(lines)).encode("utf-8")).hexdigest()


def _validated[T: FeedModel](model: type[T], payload: Any, *, portal: str, what: str) -> T:
    if not isinstance(payload, dict):
        raise InvalidInput(f"{portal} {what} is not a JSON object")
    version = payload.get("schemaVersion")
    if version != FIELD_VOICES_SCHEMA_VERSION:
        raise InvalidInput(
            f"{portal} {what} has schemaVersion {version!r}; this build reads {FIELD_VOICES_SCHEMA_VERSION}"
        )
    refused = forbidden_keys(payload)
    if refused:
        raise InvalidInput(
            f"{portal} {what} carries fields that are never sent: {', '.join(sorted(refused))}"
        )
    try:
        parsed = model.model_validate(payload)
    except ValidationError as error:
        raise InvalidInput(f"{portal} {what} breaks the contract: {first_problem(error)}") from None
    if getattr(parsed, "portal", None) != portal:
        raise InvalidInput(
            f"the {portal} address answered with a {what} from {getattr(parsed, 'portal', None)}"
        )
    return parsed


def _refuse_other_request(page: VoicesPage, craft_slug: str, cursor: str | None) -> None:
    if page.craft_slug != craft_slug or page.cursor != cursor:
        raise InvalidInput(
            f"{page.portal} answered {page.craft_slug} at cursor {page.cursor!r} "
            f"when asked for {craft_slug} at cursor {cursor!r}"
        )


def _refuse_other_image_hosts(page: PhotographsPage, image_hosts: frozenset[str]) -> None:
    for photograph in page.photographs:
        if urlsplit(photograph.image.url).hostname not in image_hosts:
            raise InvalidInput(
                f"{page.portal} photograph {photograph.id} is served from a host "
                "that FIELD_VOICES_IMAGE_HOSTS does not list"
            )
