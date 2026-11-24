from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.core.roles import Capability, can
from app.models import User
from app.research.published_edits import NOTHING_CHANGES, StagedEdit, moved_fields
from app.research.review_labels import cut_label
from app.research.review_queue import COMPONENTS, FACTS, IMAGES, LAYERS, LAYOUTS, READINGS, STAGES, STRUCTURE
from app.research.staged_reviews import EDIT, REMOVE, SOURCES, StagedDecision

from .published_components import PUBLISHED_COMPONENTS
from .published_facts import PUBLISHED_FACTS
from .published_kinds import Carried, PublishedKind, PublishedLine, PublishedQuery, PublishedRef, ref_of
from .published_layers import PUBLISHED_LAYERS
from .published_layouts import PUBLISHED_LAYOUTS
from .published_pictures import PUBLISHED_PICTURES
from .published_readings import PUBLISHED_READINGS
from .published_sources import PUBLISHED_SOURCES
from .published_stages import PUBLISHED_STAGES
from .published_structure import PUBLISHED_STRUCTURE
from .review_queue_errors import NotYourQueue

__all__ = [
    "PUBLISHED_KINDS",
    "Carried",
    "PublishedKind",
    "carry_out",
    "published_before",
    "published_fields",
    "published_id",
    "published_label",
    "published_lines",
]

NOT_AN_ADMIN = "Changing published content is for Admins and Master Admins."
VERBS = MappingProxyType({REMOVE: "Remove", EDIT: "Edit"})
LISTED_ELSEWHERE = MappingProxyType(
    {
        FACTS: "get_facts lists a page's facts with their ids; open one here by its id.",
        COMPONENTS: "list_components lists the components with their labels; name one by its label.",
        SOURCES: "get_facts gives each fact's sources with their ids; open one here by its id.",
    }
)

PUBLISHED_KINDS: Mapping[str, PublishedKind] = MappingProxyType(
    {
        FACTS: PUBLISHED_FACTS,
        COMPONENTS: PUBLISHED_COMPONENTS,
        LAYOUTS: PUBLISHED_LAYOUTS,
        STRUCTURE: PUBLISHED_STRUCTURE,
        READINGS: PUBLISHED_READINGS,
        LAYERS: PUBLISHED_LAYERS,
        STAGES: PUBLISHED_STAGES,
        SOURCES: PUBLISHED_SOURCES,
        IMAGES: PUBLISHED_PICTURES,
    }
)


async def published_label(session: AsyncSession, decision: StagedDecision) -> str | None:
    name = await PUBLISHED_KINDS[decision.kind].name(session, ref_of(decision))
    if name is None:
        return None
    return cut_label(f"{VERBS[decision.action]} {name}{_scope(decision)}")


def _scope(decision: StagedDecision) -> str:
    if (decision.kind, decision.action) != (COMPONENTS, REMOVE):
        return ""
    named = decision.craft or decision.family
    return " from every page" if named is None else f" from the page of {named}"


async def published_id(session: AsyncSession, kind: str, label: str) -> uuid.UUID | None:
    handled = PUBLISHED_KINDS.get(kind)
    return None if handled is None or handled.find is None else await handled.find(session, label)


async def published_before(session: AsyncSession, decision: StagedDecision) -> StagedDecision | None:
    if decision.action != EDIT or decision.edit is None:
        return decision
    reader = PUBLISHED_KINDS[decision.kind].editable
    editable = None if reader is None else await reader(session, ref_of(decision))
    if editable is None:
        return None
    fields = editable.fields_of(decision.edit.fields)
    before = {name: editable.current.get(name) for name in fields}
    if not moved_fields(fields, before):
        raise InvalidInput(NOTHING_CHANGES)
    return decision.model_copy(update={"edit": StagedEdit(fields=fields, before=before)})


async def carry_out(
    session: AsyncSession, decision: StagedDecision, reviewer: User, *, now: datetime
) -> Carried:
    if not can(reviewer, Capability.REVIEW_CONTRIBUTIONS):
        raise NotYourQueue(NOT_AN_ADMIN)
    return await PUBLISHED_KINDS[decision.kind].actions[decision.action](session, decision, reviewer, now)


async def published_lines(session: AsyncSession, query: PublishedQuery) -> list[PublishedLine]:
    lister = PUBLISHED_KINDS[query.kind].listed
    if lister is None:
        raise InvalidInput(LISTED_ELSEWHERE[query.kind])
    return await lister(session, query)


async def published_fields(session: AsyncSession, ref: PublishedRef) -> tuple[str, dict[str, Any]] | None:
    handled = PUBLISHED_KINDS[ref.kind]
    name = await handled.name(session, ref)
    if name is None:
        return None
    editable = None if handled.editable is None else await handled.editable(session, ref)
    return name, {} if editable is None else dict(editable.current)
