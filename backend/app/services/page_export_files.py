from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING

from app.core.errors import InvalidInput
from app.research.export_links import PAGE_EXPORT_FORMATS, ExportLink
from app.research.monograph_document import ENGLISH, MonographDocument
from app.research.vocabulary import ANSWER_LANGUAGE_SPECS

from .export_files import ExportTools
from .export_store import BuiltExport, ExportFile, stored_export_link
from .naming import export_file_name

if TYPE_CHECKING:
    from .page_export_model import PageExport

__all__ = [
    "PAGE_ENTITIES",
    "PAGE_EXPORT_OWNER",
    "PAGE_EXPORT_WHAT",
    "page_export_link",
    "page_file",
    "page_file_name",
]

PAGE_EXPORT_OWNER = uuid.UUID(int=1)
PAGE_EXPORT_WHAT = "Export"
PAGE_ENTITIES: Mapping[str, str] = MappingProxyType(
    {"craft": "Craft-Page", "family": "Family-Page", "category": "Category-Page"}
)
NOT_A_FORMAT = "A page is exported as {formats}, not {fmt!r}"


def _laid_out(document: MonographDocument) -> PageExport:
    from .page_export_document import export_specs, page_export

    return page_export(document, export_specs(document))


def _pdf(document: MonographDocument) -> bytes:
    from .page_export_pdf import page_pdf

    return page_pdf(_laid_out(document))


def _docx(document: MonographDocument) -> bytes:
    from .page_export_docx import page_docx

    return page_docx(_laid_out(document))


RENDERERS: Mapping[str, Callable[[MonographDocument], bytes]] = MappingProxyType({"pdf": _pdf, "docx": _docx})


def page_file(document: MonographDocument, fmt: str) -> bytes:
    render = RENDERERS.get(fmt)
    if render is None:
        raise InvalidInput(NOT_A_FORMAT.format(formats=" or ".join(PAGE_EXPORT_FORMATS), fmt=fmt))
    return render(document)


def page_file_name(document: MonographDocument, fmt: str, tools: ExportTools) -> str:
    language = None if document.language == ENGLISH else ANSWER_LANGUAGE_SPECS[document.language].label
    return export_file_name(
        entity=PAGE_ENTITIES[document.subject_kind],
        made_at=tools.clock(),
        craft=document.title,
        subject=language,
        version=document.version,
        what=PAGE_EXPORT_WHAT,
        ext=fmt,
    )


async def page_export_link(
    tools: ExportTools, document: MonographDocument, *, served: str, fmt: str
) -> ExportLink:
    made_from = {
        "page": [document.subject_kind, document.subject_slug],
        "served": served,
        "language": document.language,
    }

    async def build() -> BuiltExport:
        return BuiltExport(await asyncio.to_thread(page_file, document, fmt))

    export = ExportFile(
        owner_id=PAGE_EXPORT_OWNER,
        fmt=fmt,
        file_name=page_file_name(document, fmt, tools),
        made_from=made_from,
    )
    return await stored_export_link(tools.objects, export, build, now=tools.clock(), builds=tools.builds)
