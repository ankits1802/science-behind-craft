from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.core.errors import InvalidInput
from app.research.evidence import EvidenceItem, SearchQuery, SourceDocument

from ..adapter import HttpSourceAdapter, build_document
from ..records import UnusableRecord, https_or_none, markup_text, partial_date_of, title_of
from .mediawiki import (
    WIKIMEDIA_PUBLISHER,
    WIKIMEDIA_RATE,
    action_api,
    language_and_native,
    page_revision,
    pages_in_order,
    primary_language,
    with_language,
)

__all__ = ["COMMONS_RATE", "WikimediaCommonsAdapter", "file_metadata"]

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_RATE = WIKIMEDIA_RATE
FILE_NAMESPACE = 6
EXTMETADATA = (
    "ObjectName",
    "ImageDescription",
    "DateTimeOriginal",
    "Artist",
    "Credit",
    "LicenseShortName",
    "LicenseUrl",
    "AttributionRequired",
)
FILE_PROPS = {
    "prop": "imageinfo|info|revisions",
    "inprop": "url",
    "rvprop": "ids|timestamp",
    "iiprop": "url|mime|extmetadata",
    "iiextmetadatafilter": "|".join(EXTMETADATA),
}
DOCUMENT_LINES = (
    ("description", ""),
    ("date", "Date: "),
    ("author", "Author: "),
    ("credit", "Credit: "),
    ("licence", "Licence: "),
)
ISO_DATE = re.compile(r"^\d{4}(-\d{2}){0,2}([ T]|$)")
PAGE_ID = re.compile(r"^[1-9]\d*$")


class WikimediaCommonsAdapter(HttpSourceAdapter):
    name = "wikimedia_commons"

    async def _search_records(self, query: SearchQuery, k: int) -> list[Any]:
        language = primary_language(query.language)
        params = FILE_PROPS | {
            "action": "query",
            "generator": "search",
            "gsrsearch": query.text,
            "gsrnamespace": str(FILE_NAMESPACE),
            "gsrlimit": str(k),
            "iiextmetadatalanguage": language,
        }
        return [(page, language) for page in pages_in_order(await action_api(self.http, COMMONS_API, params))]

    def _item(self, record: Any, retrieved_at: datetime) -> EvidenceItem:
        page, language = record
        meta = file_metadata(page)
        if meta["licence"] is None:
            raise UnusableRecord("no licence")
        url = https_or_none(page.get("canonicalurl") or page.get("fullurl"))
        if url is None:
            raise UnusableRecord("no https description page")
        revision = page_revision(page)
        file_title = title_of(page.get("title"))
        return EvidenceItem(
            id=f"{self.name}:{with_language(str(page['pageid']), language)}",
            adapter=self.name,
            tier=self.tier,
            source_type="OTHER",
            url=url,
            title=meta["title"] or file_title.removeprefix("File:"),
            authors=[meta["author"]] if meta["author"] else [],
            published=meta["published"],
            retrieved_at=retrieved_at,
            licence=meta["licence"],
            attribution=_attribution(meta),
            publisher=WIKIMEDIA_PUBLISHER,
            trust="C",
            external_ids={
                "commons_file": file_title,
                "commons_media": f"M{page['pageid']}",
                "revision": revision.id,
            },
        )

    async def _fetch_document(self, native: str, retrieved_at: datetime) -> SourceDocument:
        language, page_id = language_and_native(native)
        if not PAGE_ID.match(page_id):
            raise InvalidInput(f"{native!r} is not a Wikimedia Commons page id")
        params = FILE_PROPS | {"action": "query", "pageids": page_id, "iiextmetadatalanguage": language}
        pages = pages_in_order(await action_api(self.http, COMMONS_API, params))
        if not pages or pages[0].get("missing") or pages[0].get("ns") != FILE_NAMESPACE:
            raise self._not_found(native, "no file")
        item = self._item((pages[0], language), retrieved_at)
        return build_document(item, _document_text(item.title, file_metadata(pages[0])), "EXCERPT")


def file_metadata(page: dict[str, Any]) -> dict[str, str | None]:
    if not page.get("pageid") or page.get("ns") != FILE_NAMESPACE:
        raise UnusableRecord("not a file page")
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata") or {}
    date = _field(meta, "DateTimeOriginal")
    return {
        "title": _field(meta, "ObjectName"),
        "description": _field(meta, "ImageDescription"),
        "date": date,
        "published": partial_date_of(date) if date and ISO_DATE.match(date) else None,
        "author": _field(meta, "Artist"),
        "credit": _field(meta, "Credit"),
        "licence": _field(meta, "LicenseShortName"),
        "licence_url": https_or_none(_field(meta, "LicenseUrl")),
    }


def _field(meta: dict[str, Any], name: str) -> str | None:
    return markup_text((meta.get(name) or {}).get("value"))


def _attribution(meta: dict[str, str | None]) -> str:
    licence = meta["licence"] or ""
    if meta["licence_url"]:
        licence = f"{licence} ({meta['licence_url']})"
    parts = [meta["author"], licence, "via Wikimedia Commons"]
    return ", ".join(part for part in parts if part)


def _document_text(title: str, meta: dict[str, str | None]) -> str:
    lines = [title]
    lines.extend(f"{label}{meta[key]}" for key, label in DOCUMENT_LINES if meta[key])
    return "\n".join(lines)
