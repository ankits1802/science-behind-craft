from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import User
from app.research.base import ContractModel
from app.research.page_revalidation import PageOwners
from app.research.published_edits import edited_fields, field_label, moved_fields
from app.research.staged_reviews import StagedDecision

from .open_work_subjects import WorkSubject

__all__ = [
    "LIST_MAX",
    "NO_ITEM",
    "Carried",
    "Doer",
    "Editable",
    "Lister",
    "Namer",
    "PublishedKind",
    "PublishedLine",
    "PublishedQuery",
    "PublishedRef",
    "Reader",
    "checked_edit",
    "ref_of",
]

LIST_MAX = 25
NO_ITEM = "No published {kind} has the id {id}."
NOT_EDITED = "This item is removed, not edited."
EDIT_NAMES = "An edit names the fields it changes."
MOVED = (
    "{fields} changed after this edit was staged, so it would undo someone else's change: stage the edit "
    "again from what the page shows now."
)


@dataclass(frozen=True)
class PublishedRef:
    kind: str
    id: uuid.UUID
    entry: str | None = None


@dataclass(frozen=True)
class Carried:
    message: str
    owners: PageOwners
    marks: tuple[str, ...] = ()
    changed: PageOwners | None = None

    @property
    def reached(self) -> PageOwners:
        return self.owners if self.changed is None else self.changed


@dataclass(frozen=True)
class Editable:
    current: Mapping[str, Any]
    model: type[ContractModel] | None
    refusal: str | None = None

    def fields_of(self, given: Mapping[str, Any]) -> dict[str, Any]:
        if self.model is None:
            raise InvalidInput(self.refusal or NOT_EDITED)
        return edited_fields(self.model, given)


@dataclass(frozen=True)
class PublishedQuery:
    kind: str
    page: WorkSubject | None
    offset: int = 0
    limit: int = LIST_MAX


@dataclass(frozen=True)
class PublishedLine:
    id: uuid.UUID
    name: str
    entry: str | None = None


Namer = Callable[[AsyncSession, PublishedRef], Awaitable[str | None]]
Finder = Callable[[AsyncSession, str], Awaitable[uuid.UUID | None]]
Doer = Callable[[AsyncSession, StagedDecision, User, datetime], Awaitable[Carried]]
Reader = Callable[[AsyncSession, PublishedRef], Awaitable[Editable | None]]
Lister = Callable[[AsyncSession, PublishedQuery], Awaitable[list[PublishedLine]]]


@dataclass(frozen=True)
class PublishedKind:
    noun: str
    name: Namer
    actions: Mapping[str, Doer]
    listed: Lister | None = None
    find: Finder | None = None
    editable: Reader | None = None


def ref_of(decision: StagedDecision) -> PublishedRef:
    return PublishedRef(decision.kind, decision.id, decision.entry)


def checked_edit(decision: StagedDecision, editable: Editable) -> dict[str, Any]:
    if decision.edit is None:
        raise InvalidInput(EDIT_NAMES)
    fields = editable.fields_of(decision.edit.fields)
    moved = moved_fields(editable.current, decision.edit.before or {})
    if moved:
        raise InvalidInput(MOVED.format(fields=", ".join(field_label(name) for name in moved)))
    return fields
