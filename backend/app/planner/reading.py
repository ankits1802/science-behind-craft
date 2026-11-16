from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from app.research.evidence import EvidenceItem, OpenAccessLocator, SourceAdapter, SourceDocument
from app.research.evidence_pack import PackedEvidence
from app.research.fetcher import Fetcher, FetchRequest
from app.sources.adapter import build_document
from app.sources.fetcher_client import FETCHER_SERVICE

from .failures import FailureLog
from .policy import DOCUMENT_TIMEOUT_SECONDS, LIVE_BUDGETS, READ_ATTEMPT_FACTOR, READ_CONCURRENCY

__all__ = [
    "FETCH_STAGE",
    "LOCATE_STAGE",
    "DocumentReader",
    "LiveSources",
    "reading_order",
]

FETCH_STAGE = "FETCH"
LOCATE_STAGE = "LOCATE"


@dataclass(frozen=True)
class LiveSources:
    searchers: tuple[SourceAdapter, ...]
    fetcher: Fetcher | None = None
    locator: OpenAccessLocator | None = None
    doi_source: SourceAdapter | None = None

    def __post_init__(self) -> None:
        names = [searcher.name for searcher in self.searchers]
        if len(set(names)) != len(names):
            raise ValueError(f"live searchers have distinct names, not {names}")


def reading_order(evidence: Sequence[PackedEvidence], facet_count: int) -> list[PackedEvidence]:
    chosen: dict[str, PackedEvidence] = {}
    for facet_index in range(facet_count):
        best = next((e for e in evidence if facet_index in e.facet_indexes and e.item.id not in chosen), None)
        if best is not None:
            chosen[best.item.id] = best
    return [*chosen.values(), *(entry for entry in evidence if entry.item.id not in chosen)]


class DocumentReader:
    def __init__(self, sources: LiveSources, *, mode: str, log: FailureLog) -> None:
        self._sources = sources
        self._searchers = {searcher.name: searcher for searcher in sources.searchers}
        self._budgets = LIVE_BUDGETS[mode]
        self._log = log
        self._gate = asyncio.Semaphore(READ_CONCURRENCY)

    async def read_best(self, ordered: Sequence[PackedEvidence], *, limit: int) -> list[SourceDocument]:
        documents: list[SourceDocument] = []
        attempts_left = limit * READ_ATTEMPT_FACTOR
        position = 0
        while len(documents) < limit and position < len(ordered) and attempts_left > 0:
            batch = ordered[position : position + min(limit - len(documents), attempts_left)]
            position += len(batch)
            attempts_left -= len(batch)
            read = await asyncio.gather(*(self.read(entry) for entry in batch))
            documents.extend(document for document in read if document is not None)
        return documents[:limit]

    async def read(self, entry: PackedEvidence) -> SourceDocument | None:
        async with self._gate:
            opened = await self.open_access_document(entry.item)
            if opened is not None:
                return opened
            searcher = self._searchers[entry.found_by[0]]
            return await self._log.guarded(
                asyncio.wait_for(searcher.fetch(entry.item.id), DOCUMENT_TIMEOUT_SECONDS),
                stage=FETCH_STAGE,
                service=searcher.name,
                target=entry.item.id,
            )

    async def open_access_document(self, item: EvidenceItem) -> SourceDocument | None:
        locator, fetcher = self._sources.locator, self._sources.fetcher
        if locator is None or fetcher is None or not self._wants_open_access(item):
            return None
        location = await self._log.guarded(
            asyncio.wait_for(locator.locate(item.doi or ""), DOCUMENT_TIMEOUT_SECONDS),
            stage=LOCATE_STAGE,
            service=locator.name,
            target=item.doi or item.id,
        )
        if location is None or not location.is_open:
            return None
        url = location.pdf_url or location.landing_url
        if url is None:
            return None
        page = await self._log.guarded(
            asyncio.wait_for(fetcher.fetch(FetchRequest(url=url)), DOCUMENT_TIMEOUT_SECONDS),
            stage=FETCH_STAGE,
            service=FETCHER_SERVICE,
            target=url,
        )
        if page is None or not page.text.strip():
            return None
        opened = item.model_copy(
            update={
                "licence": location.licence,
                "external_ids": {
                    **item.external_ids,
                    "open_access_url": page.final_url,
                    "sha256": page.sha256,
                },
            }
        )
        return build_document(opened, page.text, "FULL_TEXT", truncated=page.truncated)

    def _wants_open_access(self, item: EvidenceItem) -> bool:
        budget = self._budgets.get(item.tier)
        return bool(budget and budget.open_access and item.doi and not item.quotes)
