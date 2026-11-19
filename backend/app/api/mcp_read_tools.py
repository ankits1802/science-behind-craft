from __future__ import annotations

from pydantic import Field

from app.research.crafts import QUESTION_MAX_CHARS, SLUG_MAX_CHARS
from app.research.knowledge_api import (
    FACTS_LIMIT_DEFAULT,
    FACTS_LIMIT_MAX,
    CraftComponents,
    CraftFacts,
    CraftSection,
    FieldList,
    FoundCrafts,
)
from app.research.vocabulary import Discipline, PieceKind
from app.services import component_library, knowledge_api

from .mcp_tool_base import Arguments, NoArguments, Tool, ToolContext

__all__ = ["READ_TOOLS"]


class FindCrafts(Arguments):
    query: str = Field(
        min_length=1, max_length=QUESTION_MAX_CHARS, description="A craft's name, place or kind"
    )


class GetFacts(Arguments):
    craft_slug: str = Field(min_length=1, max_length=SLUG_MAX_CHARS, description="A slug from find_crafts")
    field: Discipline | None = Field(default=None, description="One of list_fields; every field when absent")
    query: str | None = Field(
        default=None, min_length=1, max_length=QUESTION_MAX_CHARS, description="Words to rank the facts by"
    )
    limit: int = Field(default=FACTS_LIMIT_DEFAULT, ge=1, le=FACTS_LIMIT_MAX)


class GetSection(Arguments):
    craft_slug: str = Field(min_length=1, max_length=SLUG_MAX_CHARS)
    field: Discipline


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
        description=(
            "A slug from find_crafts; also brings the shared components of its concepts, compounds "
            "and districts"
        ),
    )
    field: Discipline | None = Field(default=None, description="One of list_fields")
    kind: PieceKind | None = Field(default=None, description="One kind of component")


async def _list_fields(context: ToolContext, arguments: NoArguments) -> FieldList:
    return knowledge_api.field_list()


async def _find_crafts(context: ToolContext, arguments: FindCrafts) -> FoundCrafts:
    return await knowledge_api.found_crafts(
        context.session, context.index, arguments.query, site=context.site
    )


async def _get_facts(context: ToolContext, arguments: GetFacts) -> CraftFacts:
    return await knowledge_api.craft_facts(
        context.session,
        arguments.craft_slug,
        site=context.site,
        field=arguments.field,
        query=arguments.query,
        limit=arguments.limit,
    )


async def _get_section(context: ToolContext, arguments: GetSection) -> CraftSection:
    return await knowledge_api.craft_section(
        context.session, arguments.craft_slug, arguments.field, site=context.site
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
        "list_fields",
        "List the fields",
        "The 16 fields every fact and section is filed under, with what each covers and its chapter.",
        NoArguments,
        FieldList,
        _list_fields,
    ),
    Tool(
        "find_crafts",
        "Find crafts",
        "Up to five crafts matching a name, a local name, a place or a kind, each with its slug and page.",
        FindCrafts,
        FoundCrafts,
        _find_crafts,
    ),
    Tool(
        "get_facts",
        "Get a craft's facts",
        "The cited facts of one craft, optionally one field and ranked by words, each with its "
        "evidence level, verbatim quotes, locators and sources with their licences.",
        GetFacts,
        CraftFacts,
        _get_facts,
    ),
    Tool(
        "get_section",
        "Get a craft's section",
        "The published prose of one craft's field, each sentence with the facts it rests on; "
        "null where the section is not written yet.",
        GetSection,
        CraftSection,
        _get_section,
    ),
    Tool(
        "list_components",
        "Search the component library",
        "The registered interactive components (players, maps, molecules, charts), each with its "
        "label, title, description, kind, fields and the subjects it is keyed to. Search it before "
        "making or proposing a component: one keyed to a concept, compound or place is shared by "
        "every craft it applies to, so place it by its label rather than making another.",
        ListComponents,
        CraftComponents,
        _list_components,
    ),
)
