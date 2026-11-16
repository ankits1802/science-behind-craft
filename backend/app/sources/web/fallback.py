from __future__ import annotations

import logging

from app.core.errors import ExternalFailure, InvalidInput
from app.research.evidence import EvidenceItem, SearchQuery, SourceAdapter, SourceDocument

from ..adapter import checked_k

__all__ = ["WEB_FALLBACK_MIN_HITS", "WebSearch"]

WEB_FALLBACK_MIN_HITS = 3

logger = logging.getLogger(__name__)


class WebSearch:
    name = "web"
    tier = "T4"

    def __init__(self, primary: SourceAdapter, fallback: SourceAdapter | None = None) -> None:
        self.primary = primary
        self.fallback = fallback

    @property
    def adapters(self) -> tuple[SourceAdapter, ...]:
        return (self.primary,) if self.fallback is None else (self.primary, self.fallback)

    async def search(self, query: SearchQuery, k: int) -> list[EvidenceItem]:
        wanted = checked_k(k)
        hits, failure = await self._primary_hits(query, wanted)
        if len(hits) >= min(WEB_FALLBACK_MIN_HITS, wanted) or self.fallback is None:
            if failure is not None:
                raise failure
            return hits
        try:
            extra = await self.fallback.search(query, wanted)
        except ExternalFailure as fallback_failure:
            if failure is not None:
                raise fallback_failure from failure
            logger.warning(
                "%s fallback failed (%s); keeping %d hits",
                self.fallback.name,
                fallback_failure.kind,
                len(hits),
            )
            return hits
        return _merged(hits, extra, wanted)

    async def fetch(self, item_id: str) -> SourceDocument:
        prefix = item_id.split(":", 1)[0]
        for adapter in self.adapters:
            if adapter.name == prefix:
                return await adapter.fetch(item_id)
        raise InvalidInput(f"{item_id!r} is not an id of {', '.join(a.name for a in self.adapters)}")

    async def _primary_hits(
        self, query: SearchQuery, k: int
    ) -> tuple[list[EvidenceItem], ExternalFailure | None]:
        try:
            return await self.primary.search(query, k), None
        except ExternalFailure as failure:
            logger.warning("%s search failed (%s)", self.primary.name, failure.kind)
            return [], failure


def _merged(first: list[EvidenceItem], second: list[EvidenceItem], k: int) -> list[EvidenceItem]:
    seen = {item.source_key for item in first}
    merged = list(first)
    for item in second:
        if item.source_key not in seen:
            seen.add(item.source_key)
            merged.append(item)
    return merged[:k]
