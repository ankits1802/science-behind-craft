from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.errors import ExternalFailure, InvalidInput
from app.research.evidence import EVIDENCE_ID_MAX_CHARS, EvidenceItem, SourceDocument
from app.research.fetcher import FetchedPage, Fetcher, FetchRequest

from ..adapter import Clock, HttpSourceAdapter, build_document, utc_now
from ..http import SourceHttp
from ..records import UnusableRecord, clean_text, https_or_none, partial_date_of, title_of

__all__ = ["WEB_TRUST", "WebPageAdapter", "page_item"]

WEB_TRUST = "C"
PAGE_SOURCE_TYPES = {"text/html": "WEB_PAGE", "text/plain": "WEB_PAGE", "application/pdf": "OTHER"}


class WebPageAdapter(HttpSourceAdapter):
    tier = "T4"

    def __init__(self, http: SourceHttp, *, fetcher: Fetcher, clock: Clock = utc_now) -> None:
        super().__init__(http, clock=clock)
        self.fetcher = fetcher

    def _hit(
        self, *, url: Any, title: Any, published: Any, publisher: Any, retrieved_at: datetime
    ) -> EvidenceItem:
        page_url = https_or_none(url)
        if page_url is None:
            raise UnusableRecord("not an https URL")
        item_id = f"{self.name}:{page_url}"
        if len(item_id) > EVIDENCE_ID_MAX_CHARS:
            raise UnusableRecord(f"URL longer than an evidence id allows ({EVIDENCE_ID_MAX_CHARS})")
        return EvidenceItem(
            id=item_id,
            adapter=self.name,
            tier=self.tier,
            source_type="WEB_PAGE",
            url=page_url,
            title=title_of(title),
            published=partial_date_of(published),
            retrieved_at=retrieved_at,
            publisher=clean_text(publisher),
            trust=WEB_TRUST,
        )

    async def _fetch_document(self, native: str, retrieved_at: datetime) -> SourceDocument:
        url = https_or_none(native)
        if url is None:
            raise InvalidInput(f"{native!r} is not an https URL")
        page = await self.fetcher.fetch(FetchRequest(url=url))
        if not page.text.strip():
            raise ExternalFailure(
                f"{self.name} page {url} has no readable text", kind="not_found", service=self.name
            )
        item = page_item(self.name, url, page)
        return build_document(item, page.text, "FULL_TEXT", truncated=page.truncated)


def page_item(adapter: str, url: str, page: FetchedPage) -> EvidenceItem:
    metadata = page.metadata
    return EvidenceItem(
        id=f"{adapter}:{url}",
        adapter=adapter,
        tier="T4",
        source_type=PAGE_SOURCE_TYPES[page.content_type],
        url=page.final_url,
        title=metadata.title or page.final_url,
        authors=metadata.authors,
        published=metadata.published,
        retrieved_at=page.fetched_at,
        licence=metadata.licence,
        publisher=metadata.site_name,
        trust=WEB_TRUST,
        external_ids={"sha256": page.sha256},
    )
