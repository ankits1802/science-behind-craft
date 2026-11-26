from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import Field

from app.models.admin_work import STAGED_ACTION_VALUES, STAGED_KIND_VALUES
from app.models.enums import SOURCE_KINDS
from app.models.knowledge_pieces import LABEL_COLUMN_CHARS, LABEL_PATTERN
from app.research.crafts import SLUG_MAX_CHARS
from app.research.page_proposal_review import PAGE_SCOPE, SCOPES
from app.research.page_proposals import PageSubject
from app.research.published_edits import EDIT_FIELDS_MAX
from app.research.review_queue import CURSOR_MAX_CHARS, REASON_MAX_CHARS
from app.research.review_switch import PROPOSAL_ORIGINS
from app.research.staged_reviews import (
    AUTHORS_MAX,
    DECISIONS_PER_CALL_MAX,
    MCP_QUEUE_KINDS,
    PUBLISHED_KIND_VALUES,
    STAGED_REASON_MIN_CHARS,
)
from app.research.structure_proposals import STRUCTURE_KINDS

from .mcp_tool_base import Arguments

__all__ = [
    "OpenItem",
    "PageScopeArguments",
    "PublishedArguments",
    "ReviewQueueArguments",
    "SourceFixArguments",
    "StageArguments",
    "StagedChoice",
]

LIST_MAX = 25
OFFSET_PATTERN = r"^\d{1,5}$"

QueueKindName = Literal[*MCP_QUEUE_KINDS]


class OpenItem(Arguments):
    kind: QueueKindName
    id: uuid.UUID


class PublishedArguments(Arguments):
    kind: Literal[*PUBLISHED_KIND_VALUES]
    subject: PageSubject | None = Field(default=None, description="The page whose items of this kind to list")
    id: uuid.UUID | None = Field(
        default=None, description="Or one item to open whole, with the fields an edit changes"
    )
    label: str | None = Field(default=None, max_length=LABEL_COLUMN_CHARS, pattern=LABEL_PATTERN)
    entry: Literal[*STRUCTURE_KINDS] | None = None
    cursor: str | None = Field(default=None, pattern=OFFSET_PATTERN)


class ReviewQueueArguments(Arguments):
    kinds: list[QueueKindName] | None = Field(default=None, max_length=len(MCP_QUEUE_KINDS))
    craft_slug: str | None = Field(default=None, min_length=1, max_length=SLUG_MAX_CHARS)
    origin: Literal[*PROPOSAL_ORIGINS] | None = None
    cursor: str | None = Field(default=None, min_length=1, max_length=CURSOR_MAX_CHARS)
    limit: int = Field(default=10, ge=1, le=LIST_MAX)
    open: OpenItem | None = Field(default=None, description="One item to read whole, as its card shows it")
    published: PublishedArguments | None = Field(
        default=None, description="Published content instead of the queue, as the guide resource says"
    )
    page: uuid.UUID | None = Field(
        default=None, description="A page proposal's id: its page as it stands and as it will be"
    )


class SourceFixArguments(Arguments):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    authors: list[str] | None = Field(default=None, max_length=AUTHORS_MAX)
    year: int | None = None
    container_title: str | None = Field(default=None, min_length=1, max_length=300, description="The journal")
    kind: Literal[*SOURCE_KINDS] | None = None


class PageScopeArguments(Arguments):
    scope: Literal[*SCOPES] = Field(default=PAGE_SCOPE, description="PAGE, one CHAPTER or one COMPONENT")
    chapter: str | None = Field(default=None, min_length=1, max_length=40, description="A CHAPTER's key")
    label: str | None = Field(
        default=None, max_length=LABEL_COLUMN_CHARS, pattern=LABEL_PATTERN, description="A COMPONENT's label"
    )


class StagedChoice(Arguments):
    kind: Literal[*STAGED_KIND_VALUES]
    id: uuid.UUID | None = Field(
        default=None,
        description="The queue item, the source, the fact (SOURCES_DIFFER) or the published item",
    )
    label: str | None = Field(
        default=None,
        max_length=LABEL_COLUMN_CHARS,
        pattern=LABEL_PATTERN,
        description="Or a component by its label",
    )
    action: Literal[*STAGED_ACTION_VALUES]
    reason: str = Field(min_length=STAGED_REASON_MIN_CHARS, max_length=REASON_MAX_CHARS)
    craft_slug: str | None = Field(default=None, min_length=1, max_length=SLUG_MAX_CHARS)
    family_slug: str | None = Field(default=None, min_length=1, max_length=SLUG_MAX_CHARS)
    source: SourceFixArguments | None = None
    entry: Literal[*STRUCTURE_KINDS] | None = None
    edit: dict[str, Any] | None = Field(
        default=None, min_length=1, max_length=EDIT_FIELDS_MAX, description="An edit's fields and new values"
    )
    page: PageScopeArguments | None = Field(default=None, description="What a PAGES decision decides")


class StageArguments(Arguments):
    decisions: list[StagedChoice] = Field(min_length=1, max_length=DECISIONS_PER_CALL_MAX)
