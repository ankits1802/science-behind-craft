from __future__ import annotations

import uuid
from collections.abc import Awaitable, Sequence
from datetime import datetime
from types import MappingProxyType

from app.core.errors import AppError, InvalidInput
from app.models import DrawnPicture, User
from app.research.page_proposal_review import (
    AFTER,
    BEFORE,
    PageProposalLine,
    PageProposalView,
    proposal_line,
)
from app.research.page_render import IMAGE_BYTES_MAX
from app.services.page_proposal_pictures import kept_pictures
from app.services.page_proposal_reviews import open_page_proposals, page_proposal

from .mcp_protocol import ToolImage
from .mcp_tool_base import ToolContext

__all__ = ["PICTURE_MIME", "opened_page", "page_lines", "shown_pictures"]

PICTURE_MIME = "image/jpeg"
FIRST_SCREENS = ("first-screen-390", "first-screen-1440")
SIDE_WORDS = MappingProxyType({BEFORE: "As it stands", AFTER: "As it will be"})
CHAPTER_PREFIX = "chapter-"


async def page_lines(context: ToolContext, user: User, *, now: datetime) -> list[PageProposalLine]:
    listed = await _said(open_page_proposals(context.session, user, site=context.site, now=now))
    return [proposal_line(view) for view in listed.proposals]


async def opened_page(
    context: ToolContext, user: User, proposal_id: uuid.UUID
) -> tuple[PageProposalView, list[ToolImage]]:
    view = await _said(page_proposal(context.session, user, proposal_id, site=context.site))
    changed = [chapter.key for chapter in view.chapters]
    return view, shown_pictures(await kept_pictures(context.session, proposal_id), changed)


def shown_pictures(rows: Sequence[DrawnPicture], changed: Sequence[str]) -> list[ToolImage]:
    by_name = {(row.side, row.name): row for row in rows}
    names = [*FIRST_SCREENS, *(f"{CHAPTER_PREFIX}{key}" for key in changed)]
    wanted = [by_name[(side, name)] for name in names for side in (BEFORE, AFTER) if (side, name) in by_name]
    shown: list[ToolImage] = []
    spent = 0
    for row in wanted:
        if spent + len(row.data) > IMAGE_BYTES_MAX:
            continue
        spent += len(row.data)
        shown.append(
            ToolImage(caption=f"{SIDE_WORDS[row.side]}: {row.caption}", data=row.data, mime=PICTURE_MIME)
        )
    return shown


async def _said[T](reading: Awaitable[T]) -> T:
    try:
        return await reading
    except InvalidInput:
        raise
    except AppError as refused:
        raise InvalidInput(str(refused)) from refused
