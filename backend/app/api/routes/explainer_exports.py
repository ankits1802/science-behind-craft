from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.export_deps import EXPORT_UNAVAILABLE_DETAIL, export_tools
from app.core.db import get_session, release_connection
from app.core.deps import require
from app.core.errors import ExternalFailure, NotConfigured
from app.core.http_cache import PRIVATE_NO_CACHE
from app.core.roles import Capability
from app.models import User
from app.research.citation_export import CITATION_FORMATS, CitationExport
from app.research.citation_formats import citation_file
from app.research.explainer_versions import ExplainerVersionDocument
from app.services.apa_references import apa_references
from app.services.citation_dates import accessed_dates
from app.services.explainer_history import UNKNOWN_EXPLAINER_DETAIL, UnknownExplainer, explainer_version
from app.services.export_files import ExportTools, explainer_citations, explainer_cited, explainer_pdf_link
from app.services.naming import content_disposition, explainer_file_name

router = APIRouter(prefix="/explainers", tags=["explainers"])
logger = logging.getLogger(__name__)

CITATIONS_WHAT = "Citations"

CitationFormat = Literal[*CITATION_FORMATS]
VersionNumber = Annotated[int, Path(ge=1)]


@router.get("/{explainer_id}/versions/{version}/pdf")
async def get_explainer_pdf(
    explainer_id: uuid.UUID,
    version: VersionNumber,
    response: Response,
    *,
    user: User = Depends(require(Capability.SAVE_EXPORT)),
    session: AsyncSession = Depends(get_session),
    tools: ExportTools = Depends(export_tools),
) -> dict[str, Any]:
    document = await _owned_version(session, explainer_id, user, version)
    accessed = await accessed_dates(session, explainer_cited(document))
    await release_connection(session)
    try:
        link = await explainer_pdf_link(tools, user.id, document, accessed)
    except (ExternalFailure, NotConfigured) as error:
        logger.warning("explainer %s v%s could not be filed as a PDF: %s", explainer_id, version, error)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, EXPORT_UNAVAILABLE_DETAIL) from None
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return link.model_dump(mode="json", by_alias=True)


@router.get("/{explainer_id}/versions/{version}/citations")
async def get_citations(
    explainer_id: uuid.UUID,
    version: VersionNumber,
    response: Response,
    user: User = Depends(require(Capability.SAVE_EXPORT)),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _document, export = await _citations(session, explainer_id, user, version)
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return export.model_dump(mode="json", by_alias=True)


@router.get("/{explainer_id}/versions/{version}/citations/{fmt}")
async def get_citation_file(
    explainer_id: uuid.UUID,
    version: VersionNumber,
    fmt: CitationFormat,
    user: User = Depends(require(Capability.SAVE_EXPORT)),
    session: AsyncSession = Depends(get_session),
) -> Response:
    document, export = await _citations(session, explainer_id, user, version)
    written = citation_file(export, fmt)
    crafts = document.explainer.understood.crafts
    name = explainer_file_name(
        made_at=document.mark.created_at,
        craft=crafts[0].name if crafts else None,
        question=document.mark.question,
        version=document.mark.version,
        what=CITATIONS_WHAT,
        ext=written.extension,
    )
    return Response(
        written.text.encode("utf-8"),
        media_type=f"{written.media_type}; charset=utf-8",
        headers={
            "Content-Disposition": content_disposition(name, inline=False),
            "Cache-Control": PRIVATE_NO_CACHE,
        },
    )


async def _owned_version(
    session: AsyncSession, explainer_id: uuid.UUID, user: User, version: int
) -> ExplainerVersionDocument:
    try:
        return await explainer_version(session, explainer_id, user.id, version)
    except UnknownExplainer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, UNKNOWN_EXPLAINER_DETAIL) from None


async def _citations(
    session: AsyncSession, explainer_id: uuid.UUID, user: User, version: int
) -> tuple[ExplainerVersionDocument, CitationExport]:
    document = await _owned_version(session, explainer_id, user, version)
    accessed = await accessed_dates(session, explainer_cited(document))
    await release_connection(session)
    export = await asyncio.to_thread(explainer_citations, document, accessed, apa_references)
    return document, export
