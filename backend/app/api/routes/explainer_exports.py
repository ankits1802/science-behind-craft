from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.export_deps import citation_export, citation_file_response, explainer_pdf, export_tools
from app.core.db import get_session
from app.core.deps import require
from app.core.http_cache import PRIVATE_NO_CACHE
from app.core.roles import Capability
from app.models import User
from app.research.citation_export import CITATION_FORMATS
from app.research.explainer_versions import ExplainerVersionDocument
from app.services.explainer_history import UNKNOWN_EXPLAINER_DETAIL, UnknownExplainer, explainer_version
from app.services.export_files import ExportTools

router = APIRouter(prefix="/explainers", tags=["explainers"])

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
    link = await explainer_pdf(session, tools, user.id, document)
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
    export = await citation_export(session, await _owned_version(session, explainer_id, user, version))
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
    document = await _owned_version(session, explainer_id, user, version)
    export = await citation_export(session, document)
    return citation_file_response(document, export, fmt, {"Cache-Control": PRIVATE_NO_CACHE})


async def _owned_version(
    session: AsyncSession, explainer_id: uuid.UUID, user: User, version: int
) -> ExplainerVersionDocument:
    try:
        return await explainer_version(session, explainer_id, user.id, version)
    except UnknownExplainer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, UNKNOWN_EXPLAINER_DETAIL) from None
