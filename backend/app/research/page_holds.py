from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Literal

from pydantic import Field

from app.models.component_lifecycle import HOLD_STATES

from .base import ContractModel
from .design_critique import DesignCritique
from .page_drafts import DraftPart
from .page_proposals import PageProposalResult, PageSubject

__all__ = [
    "CONFIRM",
    "CONFIRMED",
    "DISCARD",
    "DISCARDED",
    "EXPIRED",
    "HOLD_DAYS",
    "HOLD_DECISIONS",
    "HOLD_VIEW_STATES",
    "PAGE_HOLD_SCHEMA_VERSION",
    "WAITING",
    "HoldDecision",
    "PageHoldCounts",
    "PageHoldView",
    "confirm_path",
    "hold_expiry",
    "hold_state",
]

PAGE_HOLD_SCHEMA_VERSION = 1
HOLD_DAYS = 3
WAITING, CONFIRMED, DISCARDED = HOLD_STATES
EXPIRED = "EXPIRED"
HOLD_VIEW_STATES = (*HOLD_STATES, EXPIRED)
CONFIRM, DISCARD = HOLD_DECISIONS = ("CONFIRM", "DISCARD")
CONFIRM_PATH = "/contributions/pages/{id}"

HoldViewState = Literal[*HOLD_VIEW_STATES]


class HoldDecision(ContractModel):
    decision: Literal[*HOLD_DECISIONS]


class PageHoldCounts(ContractModel):
    facts: int = Field(ge=0)
    structure: int = Field(ge=0)
    components: int = Field(ge=0)
    layout: int = Field(ge=0, le=1)
    pictures: int = Field(ge=0)
    withdrawals: int = Field(ge=0)
    translations: int = Field(ge=0)
    sections: int = Field(default=0, ge=0)


class PageHoldView(ContractModel):
    schema_version: Literal[1] = PAGE_HOLD_SCHEMA_VERSION
    id: uuid.UUID
    subject: PageSubject
    page_url: str
    state: HoldViewState
    client_name: str | None
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None
    counts: PageHoldCounts
    parts: list[DraftPart]
    preview_url: str | None
    result: PageProposalResult | None
    critique: DesignCritique | None = None
    message: str


def hold_state(stored: str, expires_at: datetime, *, now: datetime) -> str:
    return EXPIRED if stored == WAITING and expires_at <= now else stored


def hold_expiry(created_at: datetime) -> datetime:
    return created_at + timedelta(days=HOLD_DAYS)


def confirm_path(hold_id: uuid.UUID) -> str:
    return CONFIRM_PATH.format(id=hold_id)
