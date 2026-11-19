from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.research.crafts import SLUG_MAX_CHARS
from app.research.monograph_document import SUBJECT_KINDS
from app.research.page_layout import LayoutReply
from app.services.open_work_subjects import subject_by_key
from app.services.page_layouts import layout_of, subject_path

from .mcp_tool_base import Arguments, Tool, ToolContext

__all__ = ["GET_LAYOUT", "LAYOUT_TOOLS", "GetLayout"]

GET_LAYOUT = "get_layout"
GET_LAYOUT_DESCRIPTION = (
    "The layout record of one craft, family or category page: for each placed text unit or component "
    "(by its unit id or component label) its chapter, its order in the chapter, its role (HERO, OPENER, "
    "PLATE, FIGURE, SIDEBAR, PULL_QUOTE or BODY), and for a picture its crop box, size and caption "
    "override. It never holds a fact: the facts are in get_facts and get_section, the components in "
    "list_components. layout is null where the page has none yet."
)


class GetLayout(Arguments):
    subject_kind: Literal[*SUBJECT_KINDS] = Field(description="craft, family or category")
    slug: str = Field(
        min_length=1,
        max_length=SLUG_MAX_CHARS,
        pattern=r"^[A-Za-z0-9-]+$",
        description="A craft's or family's slug from find_crafts, or a category's slug",
    )


async def _get_layout(context: ToolContext, arguments: GetLayout) -> LayoutReply:
    subject = await subject_by_key(context.session, arguments.subject_kind, arguments.slug)
    return LayoutReply(
        subject_kind=subject.kind,
        subject_slug=subject.slug,
        layout=await layout_of(context.session, subject),
        page_url=f"{context.site}{subject_path(subject)}",
    )


LAYOUT_TOOLS: tuple[Tool, ...] = (
    Tool(GET_LAYOUT, "Get a page's layout", GET_LAYOUT_DESCRIPTION, GetLayout, LayoutReply, _get_layout),
)
