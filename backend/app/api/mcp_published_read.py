from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from app.core.errors import InvalidInput
from app.research.base import ContractModel, absent, empty
from app.services.open_work_subjects import subject_by_key
from app.services.published_kinds import LIST_MAX, PublishedQuery, PublishedRef
from app.services.staged_published import published_fields, published_id, published_lines

from .mcp_review_arguments import PublishedArguments
from .mcp_tool_base import ToolContext

__all__ = ["PublishedItem", "PublishedRead", "PublishedSummary", "read_published"]

NOT_FOUND = "No published {kind} item has the id {id}."
NO_LABEL = "No published {kind} item has the label {label}; list_components gives the labels."


class PublishedSummary(ContractModel):
    kind: str
    id: uuid.UUID
    entry: str | None = Field(default=None, exclude_if=absent)
    label: str


class PublishedItem(PublishedSummary):
    fields: dict[str, Any] = Field(default_factory=dict)


class PublishedRead(ContractModel):
    items: list[PublishedSummary] = Field(default_factory=list, exclude_if=empty)
    item: PublishedItem | None = Field(default=None, exclude_if=absent)
    next_cursor: str | None = None


async def read_published(context: ToolContext, asked: PublishedArguments) -> PublishedRead:
    if asked.label is not None:
        named = await published_id(context.session, asked.kind, asked.label)
        if named is None:
            raise InvalidInput(NO_LABEL.format(kind=asked.kind.lower(), label=asked.label))
        return PublishedRead(item=await _opened(context, asked, named))
    if asked.id is not None:
        return PublishedRead(item=await _opened(context, asked, asked.id))
    page = None
    if asked.subject is not None:
        page = await subject_by_key(context.session, asked.subject.kind, asked.subject.slug)
    offset = int(asked.cursor or 0)
    lines = await published_lines(context.session, PublishedQuery(asked.kind, page, offset, LIST_MAX + 1))
    items = [
        PublishedSummary(kind=asked.kind, id=line.id, entry=line.entry, label=line.name)
        for line in lines[:LIST_MAX]
    ]
    return PublishedRead(items=items, next_cursor=str(offset + LIST_MAX) if len(lines) > LIST_MAX else None)


async def _opened(context: ToolContext, asked: PublishedArguments, item_id: uuid.UUID) -> PublishedItem:
    found = await published_fields(context.session, PublishedRef(asked.kind, item_id, asked.entry))
    if found is None:
        raise InvalidInput(NOT_FOUND.format(kind=asked.kind.lower(), id=item_id))
    name, fields = found
    return PublishedItem(kind=asked.kind, id=item_id, entry=asked.entry, label=name, fields=fields)
