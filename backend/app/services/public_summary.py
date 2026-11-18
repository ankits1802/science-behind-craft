from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.research.citations import AnswerSentence, Citation, SourceRef, cited_source_ids
from app.research.craft_catalogue import CatalogueSummary, CraftCatalogue
from app.research.craft_page import HERO, CraftPage, PageClaim, PageSentence
from app.research.craft_page_context import HeroImage
from app.research.crafts import CraftRef
from app.research.public_summary import (
    PUBLIC_SUMMARY_SCHEMA_VERSION,
    FeaturedCraft,
    PlacedPoint,
    PublicSummary,
    Specimen,
)

from . import knowledge_view
from .catalogue_rows import is_reader_craft
from .craft_catalogue import load_catalogue
from .craft_page import craft_page
from .craft_page_records import craft_page_records
from .curation_keys import curated_id

__all__ = [
    "FEATURED_CRAFT_SLUGS",
    "SPECIMEN_CLAIM_KEY",
    "SPECIMEN_CRAFT_SLUG",
    "SUMMARY_CACHE_SECONDS",
    "CuratedReading",
    "PublicSummaryRecords",
    "SummaryCache",
    "curated_reading",
    "public_summary",
    "summary_records",
]

logger = logging.getLogger(__name__)

FEATURED_CRAFT_SLUGS = ("Kutch-Ajrakh", "Bastar-Dhokra", "Tikuli-Painting")
SPECIMEN_CRAFT_SLUG = "Kutch-Ajrakh"
SPECIMEN_CLAIM_KEY = "C023"
SUMMARY_CACHE_SECONDS = 86_400


@dataclass(frozen=True)
class CuratedReading:
    craft: CraftRef
    local_name: str | None
    hero: HeroImage | None
    lede: tuple[AnswerSentence, ...]
    sentences: tuple[AnswerSentence, ...]
    sources: Mapping[str, SourceRef]


@dataclass(frozen=True)
class PublicSummaryRecords:
    counts: CatalogueSummary
    reader_slugs: frozenset[str]
    curated_slugs: frozenset[str]
    points: tuple[Mapping[str, Any], ...]
    readings: Mapping[str, CuratedReading] = field(default_factory=dict)


@dataclass
class SummaryCache:
    lifetime_seconds: float = SUMMARY_CACHE_SECONDS
    clock: Callable[[], float] = time.monotonic
    _kept: tuple[float, PublicSummary] | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def summary(self, build: Callable[[], Awaitable[PublicSummary]]) -> PublicSummary:
        async with self._lock:
            now = self.clock()
            if self._kept is not None and now - self._kept[0] < self.lifetime_seconds:
                return self._kept[1]
            built = await build()
            self._kept = (now, built)
            return built


def public_summary(records: PublicSummaryRecords) -> PublicSummary:
    points = _placed(records.points, records.reader_slugs, records.curated_slugs)
    featured = [
        entry for entry in (_featured(records.readings, slug) for slug in FEATURED_CRAFT_SLUGS) if entry
    ]
    specimen = _specimen(records.readings.get(SPECIMEN_CRAFT_SLUG))
    sentences = [entry.lede for entry in featured] + ([specimen.sentence] if specimen else [])
    return PublicSummary(
        schema_version=PUBLIC_SUMMARY_SCHEMA_VERSION,
        counts=records.counts,
        featured=featured,
        specimen=specimen,
        sources=_sources(sentences, records.readings.values()),
        points=points,
    )


def curated_reading(page: CraftPage) -> CuratedReading:
    claims = {claim.id: claim for claim in page.claims}
    lede = tuple(_cited(claims, sentence) for sentence in page.overview.lede)
    sections = (_cited(claims, s) for section in page.overview.sections for s in section.sentences)
    hero = next(
        (
            HeroImage(media=picture.media, caption=picture.caption)
            for picture in page.pictures
            if picture.role == HERO
        ),
        None,
    )
    return CuratedReading(
        craft=CraftRef(slug=page.craft.slug, name=page.craft.name, path=page.craft.path),
        local_name=page.craft.local_name,
        hero=hero,
        lede=lede,
        sentences=(*lede, *sections),
        sources={source.id: source for source in page.sources},
    )


async def summary_records(session: AsyncSession) -> PublicSummaryRecords:
    catalogue = CraftCatalogue.model_validate(await load_catalogue(session))
    readers = [craft for craft in catalogue.crafts if is_reader_craft(craft)]
    curated = frozenset(craft.slug for craft in readers if craft.depth.coverage is not None)
    return PublicSummaryRecords(
        counts=catalogue.summary,
        reader_slugs=frozenset(craft.slug for craft in readers),
        curated_slugs=curated,
        points=tuple(await knowledge_view.map_points(session)),
        readings=await _curated_readings(session, curated),
    )


async def _curated_readings(session: AsyncSession, curated: frozenset[str]) -> dict[str, CuratedReading]:
    readings: dict[str, CuratedReading] = {}
    for slug in dict.fromkeys((*FEATURED_CRAFT_SLUGS, SPECIMEN_CRAFT_SLUG)):
        craft = await knowledge_view.resolve_craft(session, slug) if slug in curated else None
        if craft is None:
            logger.warning("craft %s is not curated, so the public summary leaves it out", slug)
            continue
        readings[slug] = curated_reading(craft_page(await craft_page_records(session, craft)))
    return readings


def _placed(
    points: Iterable[Mapping[str, Any]], readers: frozenset[str], curated: frozenset[str]
) -> list[PlacedPoint]:
    placed: list[PlacedPoint] = []
    for point in points:
        crafts = [craft for craft in point["crafts"] if craft["slug"] in readers]
        if crafts:
            placed.append(
                PlacedPoint(
                    key=point["key"],
                    name=point["name"],
                    latitude=point["latitude"],
                    longitude=point["longitude"],
                    total=len(crafts),
                    curated=[CraftRef.model_validate(craft) for craft in crafts if craft["slug"] in curated],
                )
            )
    return placed


def _featured(readings: Mapping[str, CuratedReading], slug: str) -> FeaturedCraft | None:
    reading = readings.get(slug)
    if reading is None:
        return None
    if not reading.lede:
        logger.warning("featured craft %s has no lede, so the public summary leaves it out", slug)
        return None
    return FeaturedCraft(
        craft=reading.craft, local_name=reading.local_name, hero=reading.hero, lede=reading.lede[0]
    )


def _specimen(reading: CuratedReading | None) -> Specimen | None:
    if reading is None:
        return None
    claim_id = str(curated_id(SPECIMEN_CRAFT_SLUG, SPECIMEN_CLAIM_KEY))
    found = next(
        (s for s in reading.sentences if any(citation.claim_id == claim_id for citation in s.citations)), None
    )
    if found is None:
        logger.warning(
            "no overview sentence of %s cites claim %s, so the public summary has no specimen",
            SPECIMEN_CRAFT_SLUG,
            SPECIMEN_CLAIM_KEY,
        )
        return None
    return Specimen(craft=reading.craft, sentence=found)


def _cited(claims: Mapping[uuid.UUID, PageClaim], sentence: PageSentence) -> AnswerSentence:
    citations: dict[str, Citation] = {}
    for claim_id in sentence.claim_ids:
        citations.update((citation.id, citation) for citation in claims[claim_id].citations)
    return AnswerSentence(
        id=sentence.id, text=sentence.text, level=sentence.level, citations=list(citations.values())
    )


def _sources(sentences: Sequence[AnswerSentence], readings: Iterable[CuratedReading]) -> list[SourceRef]:
    known = {source_id: source for reading in readings for source_id, source in reading.sources.items()}
    return [known[source_id] for source_id in cited_source_ids(sentences)]
