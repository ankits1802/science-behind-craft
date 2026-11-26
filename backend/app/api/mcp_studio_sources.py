from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from app.core.errors import InvalidInput
from app.core.mcp_scopes import CONTRIBUTE_SCOPE
from app.core.rate_limit import FACT_PROPOSALS
from app.models import SuppliedSource
from app.research.supplied_sources import READY, SuppliedSourceReply
from app.services import page_drafts, supplied_sources
from app.services.supplied_sources_identity import scholarly_lookup
from app.services.supplied_sources_pdf import FILE_BYTES_MAX, FILE_TYPES, PDF, TEXT
from app.services.supplied_sources_views import slot_path, supplied_reply

from .mcp_files import FileArgument, Staged
from .mcp_input import Question
from .mcp_questions import contributes, supplied_words, words_question
from .mcp_studio_arguments import STUDIO_DOES, SupplySourceArguments
from .mcp_tool_base import SOURCES, WRITES, Tool, ToolContext, contributor
from .oauth_hosts import endpoints_or_none
from .proposal_limits import refuse_tool_when_spent

__all__ = ["STUDIO_SOURCE_TOOLS", "SUPPLY_SOURCE", "SuppliedReply"]

NO_UPLOADS = "Files cannot be uploaded to this server; give the source's passages or its whole text instead."
NOT_ARRIVED = "The source's file has not arrived or did not pass its checks, so nothing was supplied."
WHICH_KIND = "{name} is neither a PDF nor a text file; send the source as PDF or plain text"
DESCRIPTION = (
    "Records a source the contributor can open and KalaVigyan's fetcher cannot: a paywalled paper read through "
    "a subscription or library, a book or PDF the contributor holds, an archive, or a site that refuses "
    "automated reading. It takes the source's identity (DOI, ISBN or url, title, authors, year, publisher), how "
    "and when it was read, and its words: the passages to be quoted with their locators, the whole text, or "
    "upload pdf (or text) for a private slot to PUT the file to. The identity is looked up in Crossref, "
    "OpenAlex and Semantic Scholar and the source is graded by the rubric (a confirmed paper or book A, a work "
    "found nowhere C at most). The text is kept privately for reviewers, hashed, and never shown or "
    "republished: pages show only short cited quotes. The reply's cite_as is the source as a fact's sources "
    "cite it; the QUOTES gate checks each quote verbatim against the supplied text, and the review queue shows "
    "that the fact rests on supplied text. Counts against the hour's fact proposals, like a source proposal."
)
FILE_DESCRIPTION = "The source's own PDF or text file, sent without passing through the chat; at most 20 MB"
SUPPLIED_FILE_TYPES = (FILE_TYPES[PDF], FILE_TYPES[TEXT], ".pdf", ".txt")
TEXT_SUFFIXES = frozenset({".txt", ".md"})


class SuppliedReply(SuppliedSourceReply):
    draft_id: uuid.UUID | None = None
    notices: list[str] = Field(default_factory=list)


async def _supply_source(context: ToolContext, arguments: SupplySourceArguments) -> SuppliedReply:
    user = contributor(context, "supply_source", STUDIO_DOES)
    if context.uploaded:
        return await _arrived(context, arguments)
    words = {} if arguments.gives_words() else supplied_words(context)
    if arguments.upload is not None and endpoints_or_none() is None:
        raise InvalidInput(NO_UPLOADS)
    supplied = await _recorded(context, arguments, words)
    if arguments.draft_id is not None:
        await page_drafts.attach_supplied(
            context.session, user, arguments.draft_id, supplied.row.id, now=_now()
        )
    return _reply(supplied.row, arguments, _upload_url(supplied.slot_token))


async def _recorded(
    context: ToolContext, arguments: SupplySourceArguments, words: dict[str, Any]
) -> supplied_sources.Supplied:
    user = contributor(context, "supply_source", STUDIO_DOES)
    try:
        draft = arguments.supplied(**words)
    except ValueError as refused:
        raise InvalidInput(str(refused)) from None
    await refuse_tool_when_spent(FACT_PROPOSALS, user)
    async with scholarly_lookup(context.session) as lookup:
        return await supplied_sources.supply_source(context.session, user, draft, lookup=lookup, now=_now())


async def _words_asked(context: ToolContext, arguments: SupplySourceArguments) -> Sequence[Question]:
    if arguments.gives_words() or context.files or not contributes(context):
        return []
    return [words_question(arguments.identity.title)]


async def _staged(context: ToolContext, arguments: SupplySourceArguments) -> list[Staged]:
    file = context.files[0]
    if endpoints_or_none() is None:
        raise InvalidInput(NO_UPLOADS)
    supplied = await _recorded(context, arguments, {"upload": _kind(file.mime_type, file.suffix, file.label)})
    url, expires_at = _upload_url(supplied.slot_token), supplied.row.slotExpiresAt
    if url is None or expires_at is None:
        raise InvalidInput(NO_UPLOADS)
    return [Staged(file_id=file.id, url=url, ref=str(supplied.row.id), expires_at=expires_at)]


async def _arrived(context: ToolContext, arguments: SupplySourceArguments) -> SuppliedReply:
    user = contributor(context, "supply_source", STUDIO_DOES)
    ref = next(iter(context.uploaded.values()))
    row = await supplied_sources.own_supplied(context.session, user, uuid.UUID(ref))
    if row.state != READY:
        raise InvalidInput(NOT_ARRIVED)
    if arguments.draft_id is not None:
        await page_drafts.attach_supplied(context.session, user, arguments.draft_id, row.id, now=_now())
    return _reply(row, arguments, None)


def _kind(mime: str, suffix: str, name: str) -> str:
    if mime == FILE_TYPES[PDF] or suffix == ".pdf":
        return PDF
    if mime == FILE_TYPES[TEXT] or suffix in TEXT_SUFFIXES:
        return TEXT
    raise InvalidInput(WHICH_KIND.format(name=name))


def _upload_url(slot_token: str | None) -> str | None:
    endpoints = endpoints_or_none()
    if slot_token is None or endpoints is None:
        return None
    return f"{endpoints.issuer.rstrip('/')}{slot_path(slot_token)}"


def _reply(row: SuppliedSource, arguments: SupplySourceArguments, upload_url: str | None) -> SuppliedReply:
    reply = supplied_reply(row, upload_url)
    return SuppliedReply.model_validate(
        {**reply.model_dump(), "draftId": arguments.draft_id, "notices": arguments.notices()}
    )


def _now() -> datetime:
    return datetime.now(UTC)


SUPPLY_SOURCE = Tool(
    "supply_source",
    "Supply a source you can read",
    DESCRIPTION,
    SupplySourceArguments,
    SuppliedReply,
    _supply_source,
    scope=CONTRIBUTE_SCOPE,
    annotations=WRITES,
    group=SOURCES,
    asks=_words_asked,
    files=FileArgument(
        name="file",
        accept=SUPPLIED_FILE_TYPES,
        max_size=FILE_BYTES_MAX,
        stage=_staged,
        description=FILE_DESCRIPTION,
    ),
)

STUDIO_SOURCE_TOOLS = (SUPPLY_SOURCE,)
