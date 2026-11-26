from __future__ import annotations

import uuid
from typing import Self

from pydantic import Field, model_validator

from app.research.crafts import QUESTION_MAX_CHARS, SLUG_MAX_CHARS
from app.research.knowledge_api import (
    FACTS_LIMIT_DEFAULT,
    FACTS_LIMIT_MAX,
    CraftComponents,
    CraftFacts,
    FoundCrafts,
)
from app.research.page_proposals import PageSubject
from app.research.vocabulary import Discipline, PieceKind
from app.services import category_knowledge, component_library, craft_finder, knowledge_api
from app.services.open_work_subjects import CATEGORY, subject_by_key

from .mcp_page_read import GET_PAGE
from .mcp_tool_base import Arguments, Tool, ToolContext

__all__ = ["READ_TOOLS"]

FIND_DESCRIPTION = (
    "Up to five crafts for a name, a local name, a place, a kind or what a craft is made of or done with "
    "(bell metal casting, indigo resist), ranked by the names and places matched and by the concepts, cited "
    "claims and components each craft holds, curated and covered crafts first; each with its slug, page and "
    "its cited claims per field: which fields are covered, thin or missing."
)
FACTS_DESCRIPTION = (
    "The cited facts of one craft, family or category page whole, each with its evidence level, verbatim "
    "quotes, locators, stored quantities and the figures resting on it, and the sources they cite. ids reads "
    "the facts you name, up to 50, as the page's brief (get_page, parts brief) lists them; otherwise "
    "optionally one field and ranked by words, grouped by field with counts, and every field the page holds "
    "too few facts in named as open work with its task key. A category's are the facts its page links and "
    "those proposed for it. Building a page (playbook/1), read the brief first: it lists every fact in one "
    "line, and these are the full texts of the facts a figure will cite."
)
ONE_PAGE = "name the page as subject {kind, slug} or give a craft_slug, one of them"
IDS_ALONE = "ids name the facts to read; leave field and query out"
IDS_DESCRIPTION = "The facts to read whole, by the ids the page's brief lists; field and query are left out"
COMPONENTS_DESCRIPTION = (
    "The registered interactive components (players, maps, molecules, charts), each with its label, title, "
    "description, kind, fields and the subjects it is keyed to. Search it before you fill a spec by hand: one "
    "keyed to a concept, compound or place is "
    "shared by every craft it applies to, so place it by its label rather than making another, but only when "
    "its units cite facts this page holds. The component cookbook (cookbook/1) says which tool makes each kind."
)


class FindCrafts(Arguments):
    query: str = Field(
        min_length=1,
        max_length=QUESTION_MAX_CHARS,
        description="A craft's name, place or kind, or what it is made of or done with",
    )


class GetFacts(Arguments):
    craft_slug: str | None = Field(
        default=None, min_length=1, max_length=SLUG_MAX_CHARS, description="A craft's or family's slug"
    )
    subject: PageSubject | None = Field(
        default=None,
        description="The page instead: kind craft, family or category and its slug from find_crafts",
    )
    field: Discipline | None = Field(
        default=None, description="One of the sixteen fields; every field when absent"
    )
    query: str | None = Field(
        default=None, min_length=1, max_length=QUESTION_MAX_CHARS, description="Words to rank the facts by"
    )
    limit: int = Field(default=FACTS_LIMIT_DEFAULT, ge=1, le=FACTS_LIMIT_MAX)
    ids: list[uuid.UUID] | None = Field(
        default=None, min_length=1, max_length=FACTS_LIMIT_MAX, description=IDS_DESCRIPTION
    )

    @model_validator(mode="after")
    def _one_page(self) -> Self:
        if (self.craft_slug is None) == (self.subject is None):
            raise ValueError(ONE_PAGE)
        if self.ids and (self.field is not None or self.query is not None):
            raise ValueError(IDS_ALONE)
        return self

    def wanted(self) -> list[uuid.UUID]:
        return list(dict.fromkeys(self.ids or ()))

    def most(self) -> int:
        return len(self.wanted()) or self.limit


class ListComponents(Arguments):
    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=QUESTION_MAX_CHARS,
        description="Words to search labels, titles and descriptions by, such as indigo reduction",
    )
    craft_slug: str | None = Field(
        default=None,
        min_length=1,
        max_length=SLUG_MAX_CHARS,
        description="A slug from find_crafts; also brings the shared components of its concepts, compounds and districts",
    )
    field: Discipline | None = Field(default=None, description="One of the sixteen fields")
    kind: PieceKind | None = Field(
        default=None,
        description="One component kind, as the library's components name it (fact_table, chart)",
    )


async def _find_crafts(context: ToolContext, arguments: FindCrafts) -> FoundCrafts:
    return await craft_finder.find_crafts(context.session, context.index, arguments.query, site=context.site)


async def _get_facts(context: ToolContext, arguments: GetFacts) -> CraftFacts:
    if arguments.subject is None:
        return await _craft_facts(context, arguments, str(arguments.craft_slug))
    subject = await subject_by_key(context.session, arguments.subject.kind, arguments.subject.slug)
    if subject.kind != CATEGORY:
        return await _craft_facts(context, arguments, subject.slug)
    return await category_knowledge.category_facts(
        context.session,
        subject,
        site=context.site,
        field=arguments.field,
        query=arguments.query,
        limit=arguments.most(),
        ids=arguments.wanted(),
    )


async def _craft_facts(context: ToolContext, arguments: GetFacts, slug: str) -> CraftFacts:
    return await knowledge_api.craft_facts(
        context.session,
        slug,
        site=context.site,
        field=arguments.field,
        query=arguments.query,
        limit=arguments.most(),
        held=knowledge_api.held_facts_for(context.user),
        ids=arguments.wanted(),
    )


async def _list_components(context: ToolContext, arguments: ListComponents) -> CraftComponents:
    return await component_library.library_components(
        context.session,
        slug=arguments.craft_slug,
        field=arguments.field,
        kind=arguments.kind,
        query=arguments.query,
    )


READ_TOOLS: tuple[Tool, ...] = (
    Tool(
        "find_crafts",
        "Find crafts",
        FIND_DESCRIPTION,
        FindCrafts,
        FoundCrafts,
        _find_crafts,
        shows_output=True,
    ),
    GET_PAGE,
    Tool(
        "get_facts",
        "Get a page's facts",
        FACTS_DESCRIPTION,
        GetFacts,
        CraftFacts,
        _get_facts,
        shows_output=True,
    ),
    Tool(
        "list_components",
        "Search the component library",
        COMPONENTS_DESCRIPTION,
        ListComponents,
        CraftComponents,
        _list_components,
        shows_output=True,
    ),
)
