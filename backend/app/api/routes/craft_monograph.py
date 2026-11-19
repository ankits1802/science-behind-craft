from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import public_reader, read_headers, unchanged_read
from app.core.db import get_session
from app.models import User
from app.research.monograph_document import MonographDocument
from app.services import knowledge_view
from app.services.answering import NOT_FOUND_DETAIL
from app.services.monograph_document import CRAFT_SUBJECT, document_body, document_hash, latest_document_row

router = APIRouter(prefix="/crafts", tags=["crafts"])

JSON_TYPE = "application/json"
NO_DOCUMENT_DETAIL = "This craft's page is not a monograph document yet."


@dataclass(frozen=True)
class ServedDocument:
    etag: str
    body: dict[str, Any]


@router.get("/{slug}/monograph")
async def get_craft_monograph(
    slug: str,
    request: Request,
    reader: User | None = Depends(public_reader),
    session: AsyncSession = Depends(get_session),
) -> Response:
    craft = await knowledge_view.resolve_craft(session, slug)
    if craft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND_DETAIL)
    served = await served_document(session, craft.slug)
    if served is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_DOCUMENT_DETAIL)
    unchanged = unchanged_read(request, reader, served.etag)
    if unchanged is not None:
        return unchanged
    content = json.dumps(served.body, ensure_ascii=False, separators=(",", ":"))
    return Response(content, media_type=JSON_TYPE, headers=read_headers(reader, served.etag))


async def served_document(session: AsyncSession, slug: str) -> ServedDocument | None:
    row = await latest_document_row(session, CRAFT_SUBJECT, slug)
    if row is not None:
        return ServedDocument(etag=document_etag(row.version, row.contentHash), body=row.document)
    generated = await generated_fallback(session, slug)
    if generated is None:
        return None
    return ServedDocument(
        etag=document_etag(generated.version, document_hash(generated)), body=document_body(generated)
    )


async def generated_fallback(session: AsyncSession, slug: str) -> MonographDocument | None:
    return None


def document_etag(version: int, content_hash: str) -> str:
    return f"v{version}-{content_hash}"
