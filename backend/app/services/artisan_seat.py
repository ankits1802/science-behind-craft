from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Collection, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.composer.expert_takes import TAKE_SENTENCES_MAX
from app.core.config import get_settings
from app.models import ClaimSource, FieldRecording, FieldSegment
from app.research.field_voices import FIELD_SOURCE_KIND
from app.research.quotes import quote_occurs
from app.research.retrieval import SIGNED_IN_CHUNK_ACLS, KnowledgeQuery
from app.research.vocabulary import FACT_LEVELS
from app.retrieval.field_scope import shown_recordings

from . import knowledge_view
from .answer_events import CitedClaims, cited_claims
from .builder_interface import BuildAsk, BuilderTools
from .field_voices_view import craft_name_of, field_voice
from .section_blocks import KeptSentence, prose_problems

__all__ = [
    "ARTISAN_ROLE",
    "ARTISAN_SEARCH_LIMIT",
    "FIELD_READING_ACLS",
    "Heard",
    "HeardQuote",
    "VoiceSearch",
    "artisan_take",
    "attributed",
    "stored_voices",
]

ARTISAN_ROLE = "ARTISAN"
ARTISAN_SEARCH_LIMIT = 12
FIELD_READING_ACLS = SIGNED_IN_CHUNK_ACLS


@dataclass(frozen=True)
class HeardQuote:
    claim_id: uuid.UUID
    quote: str
    name: str
    craft: str
    district: str | None


@dataclass(frozen=True)
class Heard:
    quotes: tuple[HeardQuote, ...] = ()
    cited: CitedClaims = field(default_factory=CitedClaims)


VoiceSearch = Callable[[BuildAsk], Awaitable[Heard]]


def attributed(heard: HeardQuote) -> str:
    place = f" in {heard.district} district" if heard.district else ""
    said = heard.quote.strip()
    return f"In one artisan's account, {heard.name}, who practises {heard.craft}{place}, said: “{said}”"


def artisan_take(heard: Heard, shown: Collection[str]) -> tuple[KeptSentence, ...]:
    kept: dict[uuid.UUID, KeptSentence] = {}
    for quote in heard.quotes:
        view = heard.cited.views.get(quote.claim_id)
        if view is None or view.id in kept or str(view.id) in shown or view.level not in FACT_LEVELS:
            continue
        if prose_problems([KeptSentence(quote.quote, (view.id,), (), False)], heard.cited):
            continue
        kept[view.id] = KeptSentence(attributed(quote), (view.id,), (), False)
        if len(kept) == TAKE_SENTENCES_MAX:
            break
    return tuple(kept.values())


def _field_voices_on() -> bool:
    return get_settings().field_voices_enabled


def stored_voices(tools: BuilderTools, *, enabled: Callable[[], bool] = _field_voices_on) -> VoiceSearch:
    async def heard(ask: BuildAsk) -> Heard:
        craft, retriever = ask.request.craft, tools.retriever
        if craft is None or retriever is None or tools.sessions is None or not enabled():
            return Heard()
        query = KnowledgeQuery(
            craft_slug=craft.slug,
            text=ask.request.question,
            mode=ask.request.mode,
            chunk_acls=FIELD_READING_ACLS,
            limit=ARTISAN_SEARCH_LIMIT,
        )
        hits = await retriever.search(query)
        chunks = [hit.chunk_id for hit in hits.chunks if hit.source_kind == FIELD_SOURCE_KIND]
        if not chunks:
            return Heard()
        async with tools.sessions() as session:
            return await _heard_in(session, craft.slug, chunks)

    return heard


async def _heard_in(session: AsyncSession, craft_slug: str, chunks: Sequence[uuid.UUID]) -> Heard:
    craft = await knowledge_view.resolve_craft(session, craft_slug)
    if craft is None:
        return Heard()
    cites = (
        await session.execute(
            select(ClaimSource.claimId, ClaimSource.sourceId, ClaimSource.chunkId, ClaimSource.quote).where(
                ClaimSource.chunkId.in_(list(chunks)), ClaimSource.quote.is_not(None)
            )
        )
    ).all()
    if not cites:
        return Heard()
    views, sources = await knowledge_view.claims_by_id(
        session, [cite.claimId for cite in cites], acls=FIELD_READING_ACLS
    )
    rows = (
        await session.execute(
            select(FieldSegment, FieldRecording)
            .join(FieldRecording, FieldRecording.id == FieldSegment.recordingId)
            .where(
                FieldRecording.sourceId.in_({cite.sourceId for cite in cites}), *shown_recordings(craft.id)
            )
            .order_by(FieldSegment.position)
        )
    ).all()
    order = {chunk: rank for rank, chunk in enumerate(chunks)}
    ranked = sorted(cites, key=lambda cite: order.get(cite.chunkId, len(order)))
    quotes = [found for cite in ranked if (found := _spoken(cite, rows)) is not None]
    return Heard(tuple(quotes), cited_claims(list(views.values()), sources))


def _spoken(cite: Any, rows: Sequence[Any]) -> HeardQuote | None:
    for segment, recording in rows:
        if recording.sourceId != cite.sourceId or not _says(segment, cite.quote):
            continue
        voice = field_voice(segment, recording)
        if voice is None or voice.speaker.role != ARTISAN_ROLE:
            return None
        return HeardQuote(
            claim_id=cite.claimId,
            quote=cite.quote,
            name=voice.speaker.name,
            craft=craft_name_of(recording.context or {}),
            district=voice.speaker.district,
        )
    return None


def _says(segment: FieldSegment, quote: str) -> bool:
    return quote_occurs(quote, segment.text) or bool(segment.english and quote_occurs(quote, segment.english))
