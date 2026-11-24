from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.export_deps import export_tools
from app.api.routes.craft_monograph import (
    NO_DOCUMENT_DETAIL,
    NO_VERSION_DETAIL,
    ReaderAsk,
    reader_ask,
    served_document,
)
from app.core.db import get_session, release_connection
from app.core.http_cache import PRIVATE_NO_CACHE
from app.research.export_links import PAGE_EXPORT_FORMATS
from app.research.monograph_document import MonographDocument
from app.services import knowledge_view
from app.services.answering import NOT_FOUND_DETAIL
from app.services.export_files import ExportTools
from app.services.page_export_files import page_export_link

router = APIRouter(prefix="/crafts", tags=["crafts"])

PageFormat = Literal[*PAGE_EXPORT_FORMATS]


@router.get("/{slug}/monograph/{fmt}")
async def get_craft_monograph_file(
    slug: str,
    fmt: PageFormat,
    response: Response,
    *,
    read: ReaderAsk = Depends(reader_ask),
    session: AsyncSession = Depends(get_session),
    tools: ExportTools = Depends(export_tools),
) -> dict[str, Any]:
    craft = await knowledge_view.resolve_craft(session, slug)
    if craft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    served = await served_document(session, craft, read.asked)
    if served is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, NO_VERSION_DETAIL if read.asked.version else NO_DOCUMENT_DETAIL
        )
    await release_connection(session)
    document = MonographDocument.model_validate_json(served.text)
    link = await page_export_link(tools, document, served=served.etag, fmt=fmt)
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return link.model_dump(mode="json", by_alias=True)
