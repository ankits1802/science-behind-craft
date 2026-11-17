from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ExternalFailure
from app.research.blocks import ImageItem, ImagesBlock
from app.research.image_relevance import ChosenImage, ClaimText, choose_images, topic_words
from app.research.images import ImageCandidate, ImageQuery, ImageSource
from app.research.media_refs import MediaRef

from .live_sources import LiveSourcesStore
from .media_ref_store import TEXT_RELEVANCE, SqlMediaStore

__all__ = [
    "CANDIDATES_PER_SOURCE",
    "IMAGE_SEARCH_SECONDS",
    "MediaStore",
    "SectionImages",
    "SectionImagesAsk",
    "image_search_text",
    "section_images",
]

logger = logging.getLogger(__name__)

CANDIDATES_PER_SOURCE = 10
IMAGE_SEARCH_SECONDS = 6.0


class MediaStore(Protocol):
    async def claim_texts(self, claim_ids: Sequence[uuid.UUID]) -> list[ClaimText]: ...

    async def keep(self, chosen: Sequence[ChosenImage]) -> list[MediaRef]: ...


@dataclass(frozen=True)
class SectionImagesAsk:
    block_id: str
    craft_name: str | None
    claim_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class SectionImages:
    sources: tuple[ImageSource, ...]
    store: MediaStore
    search_seconds: float = IMAGE_SEARCH_SECONDS

    async def block(self, ask: SectionImagesAsk) -> ImagesBlock | None:
        claims = await self.store.claim_texts(ask.claim_ids)
        if not claims:
            return None
        named = ask.craft_name or ""
        searched = image_search_text(named, claims)
        found = await asyncio.gather(*(self._candidates(source, searched, named) for source in self.sources))
        chosen = choose_images([c for batch in found for c in batch], claims, leave_out=named)
        if not chosen:
            return None
        kept = await self.store.keep(chosen)
        items = [
            ImageItem(media=media, claim_ids=list(image.illustration.claim_ids), relevance=TEXT_RELEVANCE)
            for media, image in zip(kept, chosen, strict=True)
        ]
        return ImagesBlock(id=ask.block_id, kind="images", version=1, reuse=None, items=items)

    async def _candidates(self, source: ImageSource, searched: str, named: str) -> list[ImageCandidate]:
        try:
            async with asyncio.timeout(self.search_seconds):
                return await _searched(source, searched, named)
        except ExternalFailure as failure:
            logger.warning("%s image search failed (%s)", source.name, failure.kind)
        except TimeoutError:
            logger.warning(
                "%s image search took over %s s; its pictures are left out", source.name, self.search_seconds
            )
        return []


async def _searched(source: ImageSource, searched: str, named: str) -> list[ImageCandidate]:
    for text in dict.fromkeys(t for t in (searched, named) if len(t) >= 2):
        found = await source.images(ImageQuery(text=text), CANDIDATES_PER_SOURCE)
        if found:
            return found
    return []


def image_search_text(craft_name: str, claims: Sequence[ClaimText]) -> str:
    words = topic_words(claims, leave_out=craft_name)
    return " ".join(part for part in (craft_name, *words) if part).strip()


async def section_images(sessions: async_sessionmaker[AsyncSession], live: LiveSourcesStore) -> SectionImages:
    return SectionImages(sources=await live.images(), store=SqlMediaStore(sessions))
