from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.document_reads import ServedDocument
from app.api.export_deps import export_tools
from app.api.public_deps import public_reader
from app.api.routes.craft_monograph import (
    NO_DOCUMENT_DETAIL,
    NO_VERSION_DETAIL,
    ReaderAsk,
    reader_ask,
    served_document,
)
from app.api.routes.page_documents import CATEGORY, FAMILY, AskedDocument, subject_document
from app.core.db import get_session, release_connection
from app.core.http_cache import PRIVATE_NO_CACHE
from app.models import User
from app.research.crafts import SLUG_MAX_CHARS
from app.research.export_links import PAGE_EXPORT_FORMATS
from app.research.monograph_document import LANGUAGE_MAX_CHARS, MonographDocument, served_language
from app.services import knowledge_view
from app.services.answering import NOT_FOUND_DETAIL
from app.services.export_files import ExportTools
from app.services.page_export_files import page_export_link

router = APIRouter(tags=["page exports"])

PageFormat = Literal[*PAGE_EXPORT_FORMATS]
Slug = Annotated[str, Path(min_length=1, max_length=SLUG_MAX_CHARS, pattern=r"^[A-Za-z0-9-]+$")]
AskedLanguage = Annotated[str | None, Query(alias="lang", max_length=LANGUAGE_MAX_CHARS)]


@dataclass(frozen=True)
class FileAsk:
    page: AskedDocument
    fmt: str


def file_ask(slug: Slug, fmt: PageFormat, lang: AskedLanguage = None) -> FileAsk:
    return FileAsk(AskedDocument(slug, served_language(lang)), fmt)


@router.get("/crafts/{slug}/monograph/{fmt}")
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
    return await _filed(session, tools, served, fmt, response)


@router.get("/families/{slug}/monograph/{fmt}")
async def get_family_page_file(
    response: Response,
    asked: FileAsk = Depends(file_ask),
    _reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
    tools: ExportTools = Depends(export_tools),
) -> dict[str, Any]:
    served = await subject_document(session, FAMILY, asked.page)
    return await _filed(session, tools, served, asked.fmt, response)


@router.get("/categories/{slug}/monograph/{fmt}")
async def get_category_page_file(
    response: Response,
    asked: FileAsk = Depends(file_ask),
    _reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
    tools: ExportTools = Depends(export_tools),
) -> dict[str, Any]:
    served = await subject_document(session, CATEGORY, asked.page)
    return await _filed(session, tools, served, asked.fmt, response)


async def _filed(
    session: AsyncSession, tools: ExportTools, served: ServedDocument, fmt: str, response: Response
) -> dict[str, Any]:
    await release_connection(session)
    document = MonographDocument.model_validate_json(served.text)
    link = await page_export_link(tools, document, served=served.etag, fmt=fmt)
    response.headers["Cache-Control"] = PRIVATE_NO_CACHE
    return link.model_dump(mode="json", by_alias=True)
