from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from app.api.public_deps import public_reader
from app.core.db import release_connection
from app.core.errors import ExternalFailure, NotConfigured
from app.core.rate_limit import export_build_attempt, retry_after_value
from app.models import User
from app.research.citation_export import CitationExport
from app.research.citation_formats import citation_file
from app.research.explainer_versions import ExplainerVersionDocument
from app.research.export_links import ExportLink
from app.research.lessons import LessonPack
from app.services.apa_references import apa_references
from app.services.citation_dates import accessed_dates
from app.services.export_files import (
    EXPLAINER_ENTITY,
    ExportTools,
    explainer_citations,
    explainer_cited,
    explainer_pdf_link,
    lesson_file_link,
    opened_export_tools,
)
from app.services.export_store import (
    BUILD_WAIT_SECONDS,
    BUSY_RETRY_SECONDS,
    EXPORT_BUILDS_AT_ONCE,
    UNREAD_REUSED_FOR,
    Admission,
    BuildRefused,
    BuildsSpent,
    ExportObjects,
    WaitedSlots,
)
from app.services.naming import content_disposition, export_file_name
from app.services.object_store import media_bucket
from app.services.page_export_files import PAGE_EXPORT_BUILDS_AT_ONCE
from app.services.shared_files import SHARED_EXPORT_BUILDS_AT_ONCE

__all__ = [
    "BUILDS_SPENT_DETAIL",
    "EXPORT_UNAVAILABLE_DETAIL",
    "build_admission",
    "citation_export",
    "citation_file_response",
    "explainer_pdf",
    "export_tools",
    "lesson_file",
    "page_export_tools",
    "refused_export",
    "shared_export_tools",
    "unavailable_export",
]

EXPORT_UNAVAILABLE_DETAIL = "This file can't be made right now. Try again later."
BUILDS_SPENT_DETAIL = (
    "Many new files were asked for from this address or account in the last few minutes. "
    "Wait a little and try again."
)
CITATIONS_WHAT = "Citations"

logger = logging.getLogger(__name__)

_export_builds = asyncio.Semaphore(EXPORT_BUILDS_AT_ONCE)
_page_export_builds = WaitedSlots(
    PAGE_EXPORT_BUILDS_AT_ONCE, wait_seconds=BUILD_WAIT_SECONDS, retry_after=BUSY_RETRY_SECONDS
)
_shared_export_builds = WaitedSlots(
    SHARED_EXPORT_BUILDS_AT_ONCE, wait_seconds=BUILD_WAIT_SECONDS, retry_after=BUSY_RETRY_SECONDS
)


async def export_tools() -> AsyncIterator[ExportTools]:
    async with opened_export_tools(_bucket(), _export_builds) as tools:
        yield tools


async def page_export_tools(
    connection: HTTPConnection, reader: User | None = Depends(public_reader)
) -> AsyncIterator[ExportTools]:
    admit = build_admission(connection, reader)
    async with opened_export_tools(_bucket(), _page_export_builds, admit=admit) as tools:
        yield tools


async def shared_export_tools(
    connection: HTTPConnection, reader: User | None = Depends(public_reader)
) -> AsyncIterator[ExportTools]:
    admit = build_admission(connection, reader)
    async with opened_export_tools(
        _bucket(), _shared_export_builds, admit=admit, unread_reused_for=UNREAD_REUSED_FOR
    ) as tools:
        yield tools


def build_admission(connection: HTTPConnection, reader: User | None) -> Admission:
    async def admit() -> None:
        allowed, wait_seconds = await export_build_attempt(connection, reader)
        if not allowed:
            raise BuildsSpent(BUILDS_SPENT_DETAIL, retry_after=wait_seconds)

    return admit


def refused_export(refused: BuildRefused) -> JSONResponse:
    spent = isinstance(refused, BuildsSpent)
    return JSONResponse(
        {"detail": refused.message},
        status_code=status.HTTP_429_TOO_MANY_REQUESTS if spent else status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={"Retry-After": retry_after_value(refused.retry_after)},
    )


def unavailable_export() -> JSONResponse:
    return JSONResponse(
        {"detail": EXPORT_UNAVAILABLE_DETAIL}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
    )


def _bucket() -> ExportObjects:
    objects = media_bucket()
    if objects is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, EXPORT_UNAVAILABLE_DETAIL)
    return objects


async def citation_export(session: AsyncSession, document: ExplainerVersionDocument) -> CitationExport:
    accessed = await accessed_dates(session, explainer_cited(document))
    await release_connection(session)
    return await asyncio.to_thread(explainer_citations, document, accessed, apa_references)


def citation_file_response(
    document: ExplainerVersionDocument, export: CitationExport, fmt: str, headers: dict[str, str]
) -> Response:
    written = citation_file(export, fmt)
    crafts = document.explainer.understood.crafts
    name = export_file_name(
        entity=EXPLAINER_ENTITY,
        made_at=document.mark.created_at,
        craft=crafts[0].name if crafts else None,
        subject=document.mark.question,
        version=document.mark.version,
        what=CITATIONS_WHAT,
        ext=written.extension,
    )
    return Response(
        written.text.encode("utf-8"),
        media_type=f"{written.media_type}; charset=utf-8",
        headers={**headers, "Content-Disposition": content_disposition(name, inline=False)},
    )


async def explainer_pdf(
    session: AsyncSession, tools: ExportTools, owner_id: uuid.UUID, document: ExplainerVersionDocument
) -> ExportLink:
    accessed = await accessed_dates(session, explainer_cited(document))
    await release_connection(session)
    try:
        return await explainer_pdf_link(tools, owner_id, document, accessed)
    except (ExternalFailure, NotConfigured) as error:
        logger.warning(
            "explainer %s v%s could not be filed as a PDF: %s",
            document.mark.explainer_id,
            document.mark.version,
            error,
        )
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, EXPORT_UNAVAILABLE_DETAIL) from None


async def lesson_file(
    session: AsyncSession, tools: ExportTools, owner_id: uuid.UUID, pack: LessonPack, fmt: str
) -> ExportLink:
    accessed = await accessed_dates(session, pack.sources)
    await release_connection(session)
    try:
        return await lesson_file_link(tools, owner_id, pack, accessed, fmt)
    except (ExternalFailure, NotConfigured) as error:
        logger.warning("lesson %s could not be filed as %s: %s", pack.id, fmt, error)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, EXPORT_UNAVAILABLE_DETAIL) from None
