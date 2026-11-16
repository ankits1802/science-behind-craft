from __future__ import annotations

import re
import uuid
from datetime import datetime
from types import MappingProxyType
from typing import Literal, Self

from pydantic import Field, model_validator

from app.research.base import ContractModel, HttpsUrl
from app.research.crafts import CraftRef
from app.research.vocabulary import MediaKind

__all__ = [
    "ASSET_LABEL",
    "IDEMPOTENCY_KEY_PATTERN",
    "JOB_RETRIES",
    "JOB_TIMEOUT_SECONDS",
    "MAX_ACTIVE_JOBS_PER_USER",
    "MEDIA_FILE_NAME_PATTERN",
    "MEDIA_JOB_STATUSES",
    "MEDIA_MAX_CLAIMS",
    "MEDIA_MIN_CLAIMS",
    "MEDIA_OUTPUT",
    "MEDIA_PROMPT_BANS",
    "MEDIA_PROMPT_VERSION",
    "MEDIA_S3_KEY_PATTERN",
    "NAMED_GROUP_WORDS",
    "POLL_SECONDS",
    "PRESIGNED_GET_SECONDS",
    "QUEUE_CONCURRENCY",
    "REFUNDED_STATUSES",
    "STYLE_HINT_BANNED_WORDS",
    "STYLE_HINT_MAX_CHARS",
    "MediaAssetView",
    "MediaFailure",
    "MediaJobRequest",
    "MediaJobView",
    "MediaKindOption",
    "MediaLabel",
    "MediaOptions",
    "MediaStageOption",
    "MediaStageRef",
    "names_a_group",
    "style_hint_problem",
]

MEDIA_JOB_STATUSES = ("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "BLOCKED")
REFUNDED_STATUSES = ("FAILED", "BLOCKED")
IDEMPOTENCY_KEY_PATTERN = r"^[A-Za-z0-9._:-]{16,160}$"
STYLE_HINT_MAX_CHARS = 120
STYLE_HINT_PATTERN = r"^[A-Za-z0-9 ,.'-]*$"
NAMED_GROUP_WORDS = frozenset(
    {"adivasi", "biradari", "caste", "clan", "community", "gotra", "jati", "samaj", "tribal", "tribe"}
)
STYLE_HINT_BANNED_WORDS = NAMED_GROUP_WORDS | frozenset(
    {
        "alphabet",
        "brand",
        "calligraphy",
        "caption",
        "letter",
        "logo",
        "number",
        "numeral",
        "script",
        "signature",
        "text",
        "watermark",
        "word",
        "writing",
        "boy",
        "child",
        "children",
        "face",
        "girl",
        "man",
        "men",
        "people",
        "person",
        "portrait",
        "woman",
        "women",
        "attire",
        "costume",
        "dress",
        "skin",
        "border",
        "flag",
        "map",
        "ceremonial",
        "deity",
        "god",
        "goddess",
        "idol",
        "religious",
        "ritual",
        "sacred",
        "shrine",
        "temple",
        "worship",
        "bypass",
        "disregard",
        "forget",
        "ignore",
        "instruction",
        "override",
        "prompt",
        "rule",
        "system",
    }
)
MEDIA_PROMPT_VERSION = "media-prompt/v2"
MEDIA_PROMPT_BANS = (
    "no text, letters or numbers",
    "no logos or brand marks",
    "no faces of real people",
    "no maps, borders or flags",
    "no ceremonial or sacred objects",
    "no depiction of a community or caste as a group",
    "no stereotyped dress or skin tone",
)
MEDIA_MIN_CLAIMS = 2
MEDIA_MAX_CLAIMS = 8
QUEUE_CONCURRENCY = MappingProxyType({"IMAGE": 4, "VIDEO": 2})
MAX_ACTIVE_JOBS_PER_USER = 3
JOB_TIMEOUT_SECONDS = 240
JOB_RETRIES = 2
POLL_SECONDS = 3
PRESIGNED_GET_SECONDS = 900
ASSET_LABEL = "AI illustration"
MEDIA_OUTPUT = MappingProxyType(
    {
        "IMAGE": MappingProxyType({"mime": "image/png", "extension": "png", "size": "1K"}),
        "VIDEO": MappingProxyType(
            {
                "mime": "video/mp4",
                "extension": "mp4",
                "seconds": 8,
                "resolution": "720p",
                "aspectRatio": "16:9",
                "audio": False,
            }
        ),
    }
)
_ENTITY = r"Generated-(?P<entity>Image|Video)"
_LEAF = (
    rf"KalaVigyan_{_ENTITY}_\d{{4}}-\d{{2}}-\d{{2}}_\d{{4}}(?:_[A-Za-z0-9-]+){{0,3}}"
    r"_(?P<what>Image|Video)_Step-\d{2}\.(?P<ext>png|mp4)"
)
MEDIA_FILE_NAME_PATTERN = rf"^{_LEAF}$"
MEDIA_S3_KEY_PATTERN = rf"^media/[0-9a-f-]{{36}}/[0-9a-f]{{32}}/{_LEAF}$"

MediaJobStatus = Literal[*MEDIA_JOB_STATUSES]


class MediaJobRequest(ContractModel):
    kind: MediaKind
    stage_id: uuid.UUID
    idempotency_key: str = Field(pattern=IDEMPOTENCY_KEY_PATTERN)
    style_hint: str | None = Field(default=None, max_length=STYLE_HINT_MAX_CHARS)

    @model_validator(mode="after")
    def _a_harmless_style_hint(self) -> Self:
        problem = style_hint_problem(self.style_hint)
        if problem:
            raise ValueError(problem)
        return self


class MediaStageRef(ContractModel):
    id: uuid.UUID
    ordinal: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=300)


class MediaLabel(ContractModel):
    text: Literal[ASSET_LABEL]
    model: str = Field(min_length=1, max_length=120)
    generated_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class MediaAssetView(ContractModel):
    id: uuid.UUID
    mime: str
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    duration_seconds: float | None = Field(gt=0)
    url: HttpsUrl
    url_expires_at: datetime
    file_name: str = Field(pattern=MEDIA_FILE_NAME_PATTERN, max_length=150)
    label: MediaLabel
    alt_text: str = Field(min_length=1, max_length=1000)
    visibility: Literal["PRIVATE", "CRAFT_SHARED"]

    @model_validator(mode="after")
    def _output_matches_its_kind(self) -> Self:
        match = re.fullmatch(MEDIA_FILE_NAME_PATTERN, self.file_name)
        kind = "IMAGE" if match and match["entity"] == "Image" else "VIDEO"
        output = MEDIA_OUTPUT[kind]
        if self.mime != output["mime"] or not match or match["ext"] != output["extension"]:
            raise ValueError(f"asset {self.id} is a {output['mime']} named for its kind")
        if match["what"] != match["entity"]:
            raise ValueError(f"asset {self.id} name says what it is twice, the same way")
        if (self.duration_seconds is None) != (kind == "IMAGE"):
            raise ValueError("a video has a duration and an image has none")
        if self.duration_seconds is not None and self.duration_seconds > output["seconds"]:
            raise ValueError(f"a video lasts at most {output['seconds']} s")
        return self


class MediaFailure(ContractModel):
    reason: Literal["FAILED", "BLOCKED"]
    message: str = Field(min_length=1, max_length=300)


class MediaJobView(ContractModel):
    id: uuid.UUID
    kind: MediaKind
    status: MediaJobStatus
    craft: CraftRef
    stage: MediaStageRef
    claim_ids: list[uuid.UUID] = Field(min_length=MEDIA_MIN_CLAIMS, max_length=MEDIA_MAX_CLAIMS)
    cached: bool
    attempts: int = Field(ge=0, le=JOB_RETRIES + 1)
    refunded: bool
    poll_after_seconds: int | None
    created_at: datetime
    updated_at: datetime
    asset: MediaAssetView | None
    failure: MediaFailure | None

    @model_validator(mode="after")
    def _status_decides_the_rest(self) -> Self:
        if (self.asset is not None) != (self.status == "SUCCEEDED"):
            raise ValueError("a job has an asset exactly when it succeeded")
        if self.asset is not None and self.asset.mime != MEDIA_OUTPUT[self.kind]["mime"]:
            raise ValueError(f"{self.kind} jobs hold {MEDIA_OUTPUT[self.kind]['mime']} files")
        if (self.failure.reason if self.failure else None) != _failure_reason(self.status):
            raise ValueError("a failed or blocked job says why, and only then")
        if self.refunded != (self.status in REFUNDED_STATUSES and not self.cached):
            raise ValueError("failed and blocked jobs are refunded; nothing else is")
        settled = self.status in ("SUCCEEDED", *REFUNDED_STATUSES)
        if self.poll_after_seconds != (None if settled else POLL_SECONDS):
            raise ValueError(f"an open job asks to be polled every {POLL_SECONDS} s")
        if self.cached and (self.status != "SUCCEEDED" or self.attempts != 0):
            raise ValueError("a shared asset is returned at once, with no attempt")
        if len(set(self.claim_ids)) != len(self.claim_ids):
            raise ValueError("each claim is used once")
        return self


class MediaKindOption(ContractModel):
    kind: MediaKind
    remaining_today: int | None = Field(ge=1)


class MediaStageOption(ContractModel):
    stage_id: uuid.UUID
    kinds: list[MediaKind] = Field(min_length=1)


class MediaOptions(ContractModel):
    craft: CraftRef
    kinds: list[MediaKindOption]
    stages: list[MediaStageOption]

    @model_validator(mode="after")
    def _stages_offer_only_available_kinds(self) -> Self:
        offered = [option.kind for option in self.kinds]
        if len(set(offered)) != len(offered):
            raise ValueError("each kind is offered once")
        for stage in self.stages:
            if len(set(stage.kinds)) != len(stage.kinds) or not set(stage.kinds) <= set(offered):
                raise ValueError(f"stage {stage.stage_id} offers only kinds the asker may still make")
        if not self.kinds and self.stages:
            raise ValueError("no kind left means no stage is offered")
        return self


def style_hint_problem(hint: str | None) -> str | None:
    if hint is None:
        return None
    if not re.fullmatch(STYLE_HINT_PATTERN, hint):
        return "A style hint uses letters, digits, spaces, commas, full stops, apostrophes and hyphens only"
    banned = sorted(_word_forms(hint) & STYLE_HINT_BANNED_WORDS)
    if banned:
        return f"A style hint cannot ask for {', '.join(banned)}"
    return None


def names_a_group(text: str) -> bool:
    return bool(_word_forms(text) & NAMED_GROUP_WORDS)


def _word_forms(text: str) -> set[str]:
    forms: set[str] = set()
    for word in re.findall(r"[a-z]+", text.casefold()):
        forms.add(word)
        if word.endswith("ies"):
            forms.add(f"{word[:-3]}y")
        if word.endswith("es"):
            forms.add(word[:-2])
        if word.endswith("s"):
            forms.add(word[:-1])
    return forms


def _failure_reason(status: str) -> str | None:
    return status if status in REFUNDED_STATUSES else None
