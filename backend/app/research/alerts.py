from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from app.models.enums import NOTIFICATION_KINDS

from .base import ContractModel
from .crafts import QUESTION_MAX_CHARS, CraftRef
from .vocabulary import AnswerLanguage, Depth, Discipline

__all__ = [
    "ALERTS_SCHEMA_VERSION",
    "DIGEST_ITEMS_MAX",
    "NOTIFICATIONS_SHOWN_MAX",
    "NOTIFICATION_KINDS",
    "SAVED_EXPLAINERS_MAX",
    "AnswerImproved",
    "FacetNews",
    "Notification",
    "NotificationList",
    "SavedExplainer",
    "SavedExplainerList",
    "WeeklyDigest",
]

ALERTS_SCHEMA_VERSION = 1
SAVED_EXPLAINERS_MAX = 200
NOTIFICATIONS_SHOWN_MAX = 50
DIGEST_ITEMS_MAX = 20
MONDAY = 0

NotificationKind = Literal[*NOTIFICATION_KINDS]


class SavedExplainer(ContractModel):
    explainer_id: uuid.UUID
    question: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    craft: CraftRef | None
    facets: list[Discipline] = Field(min_length=1)
    depth: Depth
    language: AnswerLanguage
    latest_version: int = Field(ge=1)
    seen_version: int = Field(ge=1)
    saved_at: AwareDatetime
    checked_at: AwareDatetime | None

    @model_validator(mode="after")
    def _a_version_the_reader_has_seen(self) -> Self:
        if len(set(self.facets)) != len(self.facets):
            raise ValueError(f"saved explainer {self.explainer_id} lists each facet once")
        if self.seen_version > self.latest_version:
            raise ValueError(f"saved explainer {self.explainer_id} was seen at a version it has")
        return self


class SavedExplainerList(ContractModel):
    schema_version: Literal[1]
    items: list[SavedExplainer] = Field(max_length=SAVED_EXPLAINERS_MAX)

    @model_validator(mode="after")
    def _newest_saved_first_once_each(self) -> Self:
        ids = [item.explainer_id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("an explainer is saved once")
        if [item.saved_at for item in self.items] != sorted((i.saved_at for i in self.items), reverse=True):
            raise ValueError("saved explainers are listed newest saved first")
        return self


class FacetNews(ContractModel):
    facet: Discipline
    new_claims: int = Field(ge=1)


class AnswerImproved(ContractModel):
    explainer_id: uuid.UUID
    version: int = Field(ge=1)
    question: str = Field(min_length=1, max_length=QUESTION_MAX_CHARS)
    craft: CraftRef
    news: list[FacetNews] = Field(min_length=1)
    checked_at: AwareDatetime

    @model_validator(mode="after")
    def _each_facet_once(self) -> Self:
        facets = [entry.facet for entry in self.news]
        if len(set(facets)) != len(facets):
            raise ValueError(f"the news for {self.explainer_id} names each facet once")
        return self


class Notification(ContractModel):
    id: uuid.UUID
    kind: NotificationKind
    created_at: AwareDatetime
    read_at: AwareDatetime | None
    payload: AnswerImproved

    @model_validator(mode="after")
    def _read_after_it_was_made(self) -> Self:
        if self.read_at is not None and self.read_at < self.created_at:
            raise ValueError(f"notification {self.id} is read after it was made")
        return self


class NotificationList(ContractModel):
    schema_version: Literal[1]
    items: list[Notification] = Field(max_length=NOTIFICATIONS_SHOWN_MAX)
    unread: int = Field(ge=0)

    @model_validator(mode="after")
    def _newest_first_with_unread_counted(self) -> Self:
        made = [item.created_at for item in self.items]
        if made != sorted(made, reverse=True):
            raise ValueError("notifications are listed newest first")
        if self.unread < sum(item.read_at is None for item in self.items):
            raise ValueError("the unread count covers every unread notification listed")
        return self


class WeeklyDigest(ContractModel):
    schema_version: Literal[1]
    week_of: dt.date
    items: list[AnswerImproved] = Field(min_length=1, max_length=DIGEST_ITEMS_MAX)
    settings_url: str = Field(pattern=r"^https://\S+/settings$")

    @model_validator(mode="after")
    def _a_monday_once_per_explainer(self) -> Self:
        if self.week_of.weekday() != MONDAY:
            raise ValueError("a digest is dated by the Monday of its week")
        ids = [item.explainer_id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("a digest names each explainer once")
        return self
