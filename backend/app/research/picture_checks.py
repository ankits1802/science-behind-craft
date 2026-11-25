from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.media_refs import CHECK_REASON_MAX_CHARS, PICTURE_VERDICTS

from .base import ContractModel
from .crafts import CraftRef
from .media_refs import MediaRef

__all__ = [
    "AGREEING_SHOWS_MIN",
    "BATCH_DEFAULT",
    "BATCH_MAX",
    "CHECKED_QUEUE",
    "CHECK_STATES",
    "CHECK_TASK_ACCEPTANCE",
    "DOES_NOT_SHOW",
    "HIDDEN",
    "IN_REVIEW",
    "PICTURE_CHECK_SCHEMA_VERSION",
    "PICTURE_CHECK_TASK",
    "SEEN",
    "SHOWS",
    "VERDICTS_PER_CALL_MAX",
    "VERDICT_WORDS",
    "WAITING",
    "CheckState",
    "CheckedState",
    "PictureCheckReview",
    "PictureChecks",
    "PictureToCheck",
    "RecordedCheck",
    "StoredVerdict",
    "VerdictView",
    "check_key",
    "check_link_id",
    "checked_state",
    "is_check_detail",
    "state_word",
]

PICTURE_CHECK_SCHEMA_VERSION = 1
PICTURE_CHECK_TASK = "CHECK_PICTURES"
CHECKED_QUEUE = "PICTURE_CHECKS"
SHOWS, DOES_NOT_SHOW = PICTURE_VERDICTS
VERDICT_WORDS = {"shows": SHOWS, "does_not_show": DOES_NOT_SHOW}
CHECK_STATES = ("SEEN", "WAITING", "HIDDEN", "IN_REVIEW")
SEEN, WAITING, HIDDEN, IN_REVIEW = CHECK_STATES
AGREEING_SHOWS_MIN = 2
BATCH_DEFAULT = 5
BATCH_MAX = 10
VERDICTS_PER_CALL_MAX = 10
KEY_SEPARATOR = ":"
CHECK_TASK_ACCEPTANCE = (
    "Call check_pictures: it reserves a batch of searched pictures shown beside facts, most-served first, "
    "and gives each as an image. Look at each and record shows or does_not_show with a reason of 12 to "
    "300 characters saying what the picture shows. A refusal hides the picture beside that fact at once."
)

CheckState = Literal[*CHECK_STATES]
Verdict = Literal[*PICTURE_VERDICTS]


@dataclass(frozen=True)
class StoredVerdict:
    user_id: uuid.UUID | None
    shows: bool
    trusted: bool
    ruling: bool


@dataclass(frozen=True)
class CheckedState:
    vision: bool
    refused: bool
    disputed: bool


def checked_state(verdicts: Sequence[StoredVerdict]) -> CheckedState:
    rulings = [verdict for verdict in verdicts if verdict.ruling]
    if rulings:
        last = rulings[-1]
        return CheckedState(vision=last.shows, refused=not last.shows, disputed=False)
    shows = [verdict for verdict in verdicts if verdict.shows]
    if len(shows) < len(verdicts):
        return CheckedState(vision=False, refused=True, disputed=bool(shows))
    agreeing = len({verdict.user_id for verdict in shows})
    vision = any(verdict.trusted for verdict in shows) or agreeing >= AGREEING_SHOWS_MIN
    return CheckedState(vision=vision, refused=False, disputed=False)


def state_word(state: CheckedState) -> str:
    if state.disputed:
        return IN_REVIEW
    if state.refused:
        return HIDDEN
    return SEEN if state.vision else WAITING


def check_key(link_id: uuid.UUID) -> str:
    return f"{PICTURE_CHECK_TASK}{KEY_SEPARATOR}{link_id}"


def check_link_id(detail: str) -> uuid.UUID | None:
    try:
        found = uuid.UUID(detail)
    except ValueError:
        return None
    return found if str(found) == detail else None


def is_check_detail(detail: str) -> bool:
    return check_link_id(detail) is not None


class PictureToCheck(ContractModel):
    position: int = Field(ge=1)
    link_id: uuid.UUID
    fact_id: uuid.UUID
    fact: str
    craft: CraftRef | None
    title: str
    caption: str
    credit: str | None
    page_url: str
    served: int = Field(ge=0)
    reserved_until: datetime


class RecordedCheck(ContractModel):
    link_id: uuid.UUID
    state: CheckState | None = None
    refused: str | None = None


class PictureChecks(ContractModel):
    schema_version: Literal[1] = PICTURE_CHECK_SCHEMA_VERSION
    recorded: list[RecordedCheck] = Field(default_factory=list)
    pictures: list[PictureToCheck] = Field(default_factory=list)
    skipped: int = Field(default=0, ge=0)
    holding: int = Field(ge=0)
    holding_max: int = Field(ge=1)
    message: str


class VerdictView(ContractModel):
    verdict: Verdict
    reason: str | None = Field(default=None, max_length=CHECK_REASON_MAX_CHARS)
    by: str | None
    ruling: bool
    trusted: bool
    at: datetime


class PictureCheckReview(ContractModel):
    media: MediaRef
    fact_id: uuid.UUID
    fact: str
    state: CheckState
    verdicts: list[VerdictView]
