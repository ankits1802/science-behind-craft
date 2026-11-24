from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from app.core.errors import InvalidInput
from app.models.admin_work import (
    BATCH_STATUSES,
    ITEM_STATES,
    STAGED_ACTION_VALUES,
    STAGED_CORRECTION_KINDS,
    STAGED_KIND_VALUES,
    STAGED_PUBLISHED_KINDS,
    STAGED_QUEUE_KINDS,
)
from app.models.enums import SOURCE_KINDS
from app.models.knowledge import CONTAINER_TITLE_CHARS

from .base import ContractModel, absent, empty
from .crafts import SLUG_MAX_CHARS
from .published_edits import FieldChange, StagedEdit
from .review_queue import (
    APPROVE,
    COMPONENTS,
    FACTS,
    IMAGES,
    KIND_ACTIONS,
    LAYERS,
    LAYOUTS,
    ONE_HOME,
    READINGS,
    REASON_MAX_CHARS,
    STAGES,
    STRUCTURE,
)
from .structure_proposals import StructureKind

__all__ = [
    "APPLIED",
    "AUTHORS_MAX",
    "BATCHES_SHOWN",
    "BATCH_DAYS",
    "CLEAR",
    "CONFIRMED",
    "CORRECT",
    "DECISIONS_PER_CALL_MAX",
    "DISCARDED",
    "EDIT",
    "EXPIRED",
    "MCP_QUEUE_KINDS",
    "OPEN",
    "PUBLISHED_ACTIONS",
    "PUBLISHED_ACTION_VALUES",
    "PUBLISHED_KIND_VALUES",
    "PUBLISHED_ONLY_KINDS",
    "REFUSED",
    "REMOVE",
    "SKIPPED",
    "SOURCES",
    "SOURCES_DIFFER",
    "STAGED",
    "STAGED_ITEMS_PER_DAY_MAX",
    "STAGED_KIND_ACTIONS",
    "STAGED_REASON_MIN_CHARS",
    "STAGED_SCHEMA_VERSION",
    "ConfirmedItem",
    "SourceFix",
    "StagedBatchList",
    "StagedBatchView",
    "StagedConfirmation",
    "StagedDecision",
    "StagedItemView",
    "acts_on_published",
    "batch_expiry",
    "batch_status",
    "day_allowance_problem",
    "stored_decision",
]

STAGED_SCHEMA_VERSION = 1
DECISIONS_PER_CALL_MAX = 20
STAGED_ITEMS_PER_DAY_MAX = 100
STAGED_REASON_MIN_CHARS = 12
BATCH_DAYS = 3
BATCHES_SHOWN = 20
AUTHORS_MAX = 30
AUTHOR_MAX_CHARS = 200
TITLE_MAX_CHARS = 500
YEAR_MIN, YEAR_MAX = 1000, 2100
OPEN, CONFIRMED, DISCARDED = BATCH_STATUSES
EXPIRED = "EXPIRED"
STAGED, APPLIED, REFUSED, SKIPPED = ITEM_STATES
MCP_QUEUE_KINDS: tuple[str, ...] = STAGED_QUEUE_KINDS
SOURCES, SOURCES_DIFFER = STAGED_CORRECTION_KINDS
PUBLISHED_ONLY_KINDS: tuple[str, ...] = STAGED_PUBLISHED_KINDS
CORRECT, CLEAR, REMOVE, EDIT = STAGED_ACTION_VALUES[4:]
REMOVED_AND_EDITED = (REMOVE, EDIT)
PUBLISHED_ACTIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        FACTS: (EDIT,),
        COMPONENTS: REMOVED_AND_EDITED,
        LAYOUTS: (REMOVE,),
        STRUCTURE: REMOVED_AND_EDITED,
        READINGS: (REMOVE,),
        LAYERS: (REMOVE,),
        STAGES: (REMOVE,),
        SOURCES: (REMOVE,),
        IMAGES: REMOVED_AND_EDITED,
    }
)
PUBLISHED_ACTION_VALUES = frozenset(action for actions in PUBLISHED_ACTIONS.values() for action in actions)
PUBLISHED_KIND_VALUES: tuple[str, ...] = tuple(PUBLISHED_ACTIONS)
STAGED_KIND_ACTIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        **{kind: (*KIND_ACTIONS[kind], *PUBLISHED_ACTIONS.get(kind, ())) for kind in MCP_QUEUE_KINDS},
        SOURCES: (CORRECT, *PUBLISHED_ACTIONS[SOURCES]),
        SOURCES_DIFFER: (CLEAR,),
        **{kind: PUBLISHED_ACTIONS[kind] for kind in PUBLISHED_ONLY_KINDS},
    }
)
NOT_FOR_KIND = "A {kind} item is {actions}, not {action}."
REFILE_ONLY = "Only an approved fact is filed under a craft or a family's science."
ONE_PAGE = (
    "A removal takes the item off every page, or off the one page named: a craft's slug as craft, or a "
    "category's as family, not both."
)
PAGE_FOR_COMPONENTS = (
    "Only a component's removal names the one page it leaves; anything else is removed or edited wherever it "
    "is shown."
)
STAYS_PUBLISHED = (
    "A decision on published content stays one, and a decision on a waiting item stays one: stage the other "
    "anew."
)
STAYS_AN_EDIT = (
    "An edit is confirmed as it was staged, its reason alone open to change, and a removal stays a removal: "
    "stage the other anew."
)
EDIT_NEEDED = "An edit names the fields it changes as edit, and only an edit names them."
ENTRY_ONLY = "Only a removal or an edit of a structure entry names the entry's kind."
SOURCE_ONLY = "Only a source correction carries a source's corrected fields."
SOURCE_NEEDED = "A source correction names at least one corrected field."
OVER_DAY = (
    "Staging {asked} more would pass the {most} items an Admin may stage in a day; {left} are left until "
    "midnight India time."
)

StagedKind = Literal[*STAGED_KIND_VALUES]
StagedAction = Literal[*STAGED_ACTION_VALUES]
StagedReason = Annotated[str, Field(min_length=STAGED_REASON_MIN_CHARS, max_length=REASON_MAX_CHARS)]
Slug = Annotated[str, Field(min_length=1, max_length=SLUG_MAX_CHARS)]
Author = Annotated[str, Field(min_length=1, max_length=AUTHOR_MAX_CHARS)]
BatchStatus = Literal[*BATCH_STATUSES, "EXPIRED"]
ItemState = Literal[*ITEM_STATES]


class SourceFix(ContractModel):
    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX_CHARS)
    authors: list[Author] | None = Field(default=None, max_length=AUTHORS_MAX)
    year: int | None = Field(default=None, ge=YEAR_MIN, le=YEAR_MAX)
    container_title: str | None = Field(default=None, min_length=1, max_length=CONTAINER_TITLE_CHARS)
    kind: Literal[*SOURCE_KINDS] | None = None

    @model_validator(mode="after")
    def _names_a_field(self) -> Self:
        if not self.model_dump(exclude_none=True):
            raise ValueError(SOURCE_NEEDED)
        return self


class _Choice(ContractModel):
    action: StagedAction
    reason: StagedReason
    craft: Slug | None = None
    family: Slug | None = None
    source: SourceFix | None = None


class StagedDecision(_Choice):
    kind: StagedKind
    id: uuid.UUID
    entry: StructureKind | None = Field(default=None, exclude_if=absent)
    edit: StagedEdit | None = Field(default=None, exclude_if=absent)

    @model_validator(mode="after")
    def _fits_its_kind(self) -> Self:
        allowed = STAGED_KIND_ACTIONS[self.kind]
        if self.action not in allowed:
            raise ValueError(
                NOT_FOR_KIND.format(kind=self.kind, actions=" or ".join(allowed), action=self.action)
            )
        problem = _page_problem(self) if acts_on_published(self.action) else _filing_problem(self)
        problem = problem or _parts_problem(self)
        if problem is not None:
            raise ValueError(problem)
        return self

    def changed_to(self, choice: ConfirmedItem) -> StagedDecision:
        if acts_on_published(choice.action) != acts_on_published(self.action):
            raise InvalidInput(STAYS_PUBLISHED)
        if acts_on_published(self.action) and choice.action != self.action:
            raise InvalidInput(STAYS_AN_EDIT)
        fields = choice.model_dump(exclude={"id"})
        target = {"kind": self.kind, "id": self.id, "entry": self.entry, "edit": self.edit}
        return StagedDecision.model_validate({**fields, **target})


class ConfirmedItem(_Choice):
    id: uuid.UUID


class StagedConfirmation(ContractModel):
    items: list[ConfirmedItem] = Field(min_length=1, max_length=DECISIONS_PER_CALL_MAX)


class StagedItemView(ContractModel):
    id: uuid.UUID
    position: int = Field(ge=0)
    label: str
    decision: StagedDecision
    state: ItemState
    applied: StagedDecision | None = None
    outcome: str | None = None
    changes: list[FieldChange] = Field(default_factory=list, exclude_if=empty)


class StagedBatchView(ContractModel):
    id: uuid.UUID
    status: BatchStatus
    client_name: str
    proposed_by: str | None
    created_at: datetime
    expires_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None
    refresh: str | None = None
    items: list[StagedItemView]


class StagedBatchList(ContractModel):
    schema_version: Literal[1] = STAGED_SCHEMA_VERSION
    batches: list[StagedBatchView] = Field(max_length=BATCHES_SHOWN)


def stored_decision(decision: StagedDecision) -> dict[str, Any]:
    stored = decision.model_dump(mode="json", exclude_none=True)
    if decision.edit is not None:
        stored["edit"] = decision.edit.model_dump(mode="json")
    return stored


def batch_status(stored: str, expires_at: datetime, *, now: datetime) -> str:
    return EXPIRED if stored == OPEN and expires_at <= now else stored


def batch_expiry(created_at: datetime) -> datetime:
    return created_at + timedelta(days=BATCH_DAYS)


def day_allowance_problem(today: int, asked: int, *, most: int = STAGED_ITEMS_PER_DAY_MAX) -> str | None:
    if asked == 0 or today + asked <= most:
        return None
    return OVER_DAY.format(asked=asked, most=most, left=max(most - today, 0))


def _filing_problem(decision: StagedDecision) -> str | None:
    if decision.craft is not None and decision.family is not None:
        return ONE_HOME
    if (decision.craft or decision.family) is not None and (decision.kind, decision.action) != (
        FACTS,
        APPROVE,
    ):
        return REFILE_ONLY
    return None


def acts_on_published(action: str) -> bool:
    return action in PUBLISHED_ACTION_VALUES


def _page_problem(decision: StagedDecision) -> str | None:
    if decision.craft is None and decision.family is None:
        return None
    if (decision.kind, decision.action) != (COMPONENTS, REMOVE):
        return PAGE_FOR_COMPONENTS
    if decision.craft is not None and decision.family is not None:
        return ONE_PAGE
    return None


def _parts_problem(decision: StagedDecision) -> str | None:
    if (decision.edit is not None) != (decision.action == EDIT):
        return EDIT_NEEDED
    if decision.entry is not None and not (decision.kind == STRUCTURE and acts_on_published(decision.action)):
        return ENTRY_ONLY
    if (decision.source is not None) != (decision.kind == SOURCES and decision.action == CORRECT):
        return SOURCE_NEEDED if decision.action == CORRECT else SOURCE_ONLY
    return None
