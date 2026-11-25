from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated, Any

from fastapi import BackgroundTasks, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.public_deps import read_headers, unchanged_read
from app.core.db import release_connection
from app.core.rate_limit import is_web_server_read
from app.models import User
from app.research.document_parts import compact_json, document_parts, part_body
from app.services.open_work_subjects import WorkSubject
from app.services.page_revalidation import refresh_pages
from app.services.page_text_index import PageKey, stored_tag
from app.services.page_translation_serving import ServedPage, page_in_language, translated_page
from app.services.stored_document_rebuilds import rebuild_wanted, subject_owners
from app.services.stored_documents import GeneratedRead, StoredCopy, claim_refresh, superseded_copy, utc_now

__all__ = [
    "CONTENT_LANGUAGE",
    "JSON_TYPE",
    "NO_PART_DETAIL",
    "PARTS_MAX",
    "READING_MOVED_DETAIL",
    "WHOLE_DOCUMENT",
    "AskedPart",
    "AskedTag",
    "AskedVersion",
    "PartAsk",
    "ServedDocument",
    "StoredText",
    "WebRead",
    "document_response",
    "generated_at",
    "generated_in_language",
    "generated_served",
    "in_language",
    "not_found",
    "queue_rebuild",
    "refresh_drawn",
    "superseded_fallback",
    "web_read",
]

JSON_TYPE = "application/json"
CONTENT_LANGUAGE = "Content-Language"
NO_PART_DETAIL = "This monograph has no such part."
READING_MOVED_DETAIL = "This monograph has changed since its first part was read; read it again from part 0."
PARTS_MAX = 64
TAG_MAX_CHARS = 160
TAG_PATTERN = r"^[A-Za-z0-9-]+$"

AskedPart = Annotated[int | None, Query(ge=0, le=PARTS_MAX)]
AskedTag = Annotated[str | None, Query(max_length=TAG_MAX_CHARS, pattern=TAG_PATTERN)]
AskedVersion = Annotated[int | None, Query(ge=1)]


@dataclass(frozen=True)
class PartAsk:
    part: int | None = None
    tag: str | None = None


WHOLE_DOCUMENT = PartAsk()


@dataclass(frozen=True)
class ServedDocument:
    etag: str
    language: str
    text: str
    version: int
    rebuild: tuple[str, str] | None = None
    withheld: bool = False


@dataclass(frozen=True)
class WebRead:
    background: BackgroundTasks
    by_web: bool


def web_read(request: Request, background: BackgroundTasks) -> WebRead:
    return WebRead(background, is_web_server_read(request))


def not_found(detail: str, web: WebRead) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status.HTTP_404_NOT_FOUND, background=web.background)


class StoredText(Mapping[str, Any]):
    def __init__(self, text: str) -> None:
        self._text = text

    @cached_property
    def _body(self) -> dict[str, Any]:
        found: dict[str, Any] = json.loads(self._text)
        return found

    def __getitem__(self, key: str) -> Any:
        return self._body[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._body)

    def __len__(self) -> int:
        return len(self._body)


def generated_served(read: GeneratedRead) -> ServedDocument | None:
    copy = read.copy
    if copy is None:
        return None
    rebuild = (read.subject.kind, read.subject.slug) if read.rebuild else None
    return ServedDocument(copy.etag, copy.language, copy.text, copy.version, rebuild)


async def in_language(
    session: AsyncSession, page: PageKey, english: ServedPage, *, tag: str, language: str
) -> ServedPage:
    shown = await page_in_language(session, page, english, tag=tag, language=language)
    if shown.wrote:
        await release_connection(session)
    return shown.page


async def generated_in_language(
    session: AsyncSession, read: GeneratedRead, *, language: str
) -> ServedDocument | None:
    served = generated_served(read)
    if served is None or read.copy is None:
        return None
    page = (read.subject.kind, read.subject.slug)
    english = ServedPage(etag=served.etag, language=served.language, body=StoredText(served.text))
    tag = stored_tag(read.copy.version, read.copy.content_hash)
    shown = await in_language(session, page, english, tag=tag, language=language)
    if shown is english:
        return served
    return ServedDocument(
        shown.etag, shown.language, compact_json(shown.body), served.version, served.rebuild
    )


async def generated_at(
    session: AsyncSession,
    read: GeneratedRead,
    *,
    language: str,
    version: int | None,
    web: WebRead | None = None,
) -> ServedDocument | None:
    if read.copy is None:
        return None
    if version is None or version == read.copy.version:
        return await generated_in_language(session, read, language=language)
    current = generated_served(read)
    copy = await superseded_fallback(session, read.subject, version)
    if current is None or copy is None:
        await refresh_drawn(session, read, version, web)
        return None
    english = ServedPage(etag=copy.etag, language=copy.language, body=StoredText(copy.text))
    page = (read.subject.kind, read.subject.slug)
    shown = await translated_page(session, page, english, language=language)
    text = copy.text if shown is english else compact_json(shown.body)
    return ServedDocument(shown.etag, shown.language, text, copy.version, current.rebuild, copy.withheld)


async def refresh_drawn(
    session: AsyncSession, read: GeneratedRead, version: int, web: WebRead | None
) -> None:
    if web is None or not web.by_web or read.copy is None or version > read.copy.version:
        return
    if await claim_refresh(session, read.subject, now=utc_now()):
        web.background.add_task(refresh_pages, subject_owners(read.subject.kind, read.subject.slug))


async def superseded_fallback(session: AsyncSession, subject: WorkSubject, version: int) -> StoredCopy | None:
    return await superseded_copy(session, subject, version)


def queue_rebuild(background: BackgroundTasks, served: ServedDocument) -> None:
    if served.rebuild is not None:
        background.add_task(rebuild_wanted, *served.rebuild)


def document_response(
    request: Request, reader: User | None, served: ServedDocument, asked: PartAsk
) -> Response:
    if asked.tag is not None and asked.tag != served.etag:
        raise HTTPException(status.HTTP_404_NOT_FOUND, READING_MOVED_DETAIL)
    etag, content = served.etag, served.text
    if asked.part is not None:
        parts = document_parts(json.loads(served.text))
        if asked.part >= len(parts):
            raise HTTPException(status.HTTP_404_NOT_FOUND, NO_PART_DETAIL)
        etag = f"{served.etag}-p{asked.part}"
        content = compact_json(part_body(parts[asked.part], served.version, served.etag))
    unchanged = unchanged_read(request, reader, etag)
    if unchanged is not None:
        unchanged.headers[CONTENT_LANGUAGE] = served.language
        return unchanged
    headers = {**read_headers(reader, etag), CONTENT_LANGUAGE: served.language}
    return Response(content, media_type=JSON_TYPE, headers=headers)
