from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime
from types import MappingProxyType
from typing import TYPE_CHECKING

from app.core.errors import InvalidInput
from app.research.export_links import PAGE_EXPORT_FORMATS, ExportLink
from app.research.monograph_document import ENGLISH, MonographDocument
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS

from .export_files import ExportTools
from .export_store import UNREAD_REUSED_FOR, BuiltExport, ExportFile, stored_export_link
from .naming import export_file_name

if TYPE_CHECKING:
    from .page_export_model import PageExport
    from .page_export_pictures import PagePictures

__all__ = [
    "PAGE_ENTITIES",
    "PAGE_EXPORT_BUILDS_AT_ONCE",
    "PAGE_EXPORT_EDITION",
    "PAGE_EXPORT_OWNER",
    "PAGE_EXPORT_WHAT",
    "page_export_link",
    "page_file",
    "page_file_name",
]

PAGE_EXPORT_OWNER = uuid.UUID(int=1)
PAGE_EXPORT_WHAT = "Export"
PAGE_EXPORT_EDITION = 2
PAGE_EXPORT_BUILDS_AT_ONCE = 2
PAGE_ENTITIES: Mapping[str, str] = MappingProxyType(
    {"craft": "Craft-Page", "family": "Family-Page", "category": "Category-Page"}
)
NOT_A_FORMAT = "A page is exported as {formats}, not {fmt!r}"


def _pdf(export: PageExport) -> bytes:
    from .page_export_pdf import page_pdf

    return page_pdf(export)


def _docx(export: PageExport) -> bytes:
    from .page_export_docx import page_docx

    return page_docx(export)


RENDERERS: Mapping[str, Callable[[PageExport], bytes]] = MappingProxyType({"pdf": _pdf, "docx": _docx})


def page_file(document: MonographDocument, fmt: str, pictures: PagePictures | None = None) -> bytes:
    from .page_export_document import export_specs, page_export
    from .page_export_pictures import NO_PICTURES

    render = RENDERERS.get(fmt)
    if render is None:
        raise InvalidInput(NOT_A_FORMAT.format(formats=" or ".join(PAGE_EXPORT_FORMATS), fmt=fmt))
    return render(page_export(document, export_specs(document), pictures=pictures or NO_PICTURES))


def page_file_name(document: MonographDocument, fmt: str, made_at: datetime | None = None) -> str:
    language = None if document.language == ENGLISH else ANSWER_LANGUAGE_SPECS[document.language].label
    return export_file_name(
        entity=PAGE_ENTITIES[document.subject_kind],
        made_at=made_at,
        craft=document.title,
        subject=language,
        version=document.version,
        what=PAGE_EXPORT_WHAT,
        ext=fmt,
    )


async def page_export_link(
    tools: ExportTools, document: MonographDocument, *, served: str, fmt: str
) -> ExportLink:
    from .page_export_words import export_words

    made_from = {
        "page": [document.subject_kind, document.subject_slug],
        "served": served,
        "language": document.language,
        "edition": PAGE_EXPORT_EDITION,
        "words": export_words(document.language).made_from(),
    }

    async def build() -> BuiltExport:
        pictures, unread = await _page_pictures(tools, document)
        return BuiltExport(await asyncio.to_thread(page_file, document, fmt, pictures), unread)

    now = tools.clock()
    export = ExportFile(
        owner_id=PAGE_EXPORT_OWNER,
        fmt=fmt,
        file_name=page_file_name(document, fmt, now),
        made_from=made_from,
        stored_name=page_file_name(document, fmt),
        unread_reused_for=UNREAD_REUSED_FOR,
    )
    return await stored_export_link(
        tools.objects, export, build, now=now, builds=tools.builds, admit=tools.admit
    )


async def _page_pictures(
    tools: ExportTools, document: MonographDocument
) -> tuple[PagePictures, frozenset[uuid.UUID]]:
    from .page_export_document import export_specs
    from .page_export_pictures import fetched_pictures, wanted_pictures

    specs = await asyncio.to_thread(export_specs, document)
    return await fetched_pictures(wanted_pictures(document, specs), tools.pictures)
