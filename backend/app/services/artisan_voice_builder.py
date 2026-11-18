from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.models.enums import DISCIPLINES
from app.research.blocks_people import ArtisanVoiceBlock
from app.research.explainer import Block
from app.research.quotes import content_stems
from app.research.voices import VoiceQuote

from . import knowledge_view
from .builder_interface import BuildAsk, BuilderTools, Built
from .testimony_store import TestimonyQuote, approved_quotes

__all__ = [
    "ARTISAN_VOICE_FIELDS",
    "QUOTES_BY_DEPTH",
    "TESTIMONY_ORIGIN",
    "ArtisanVoiceBuilder",
    "Offered",
    "chosen_quotes",
    "voice_quote_payload",
]

logger = logging.getLogger(__name__)

ARTISAN_VOICE_FIELDS = frozenset(DISCIPLINES)
QUOTES_BY_DEPTH = {"BASIC": 1, "DETAILED": 2, "EXPERT": 3}
TESTIMONY_ORIGIN = "KALAVIGYAN"
OFFERED_MAX = 40
BLOCK_SUFFIX = "voices1"


@dataclass(frozen=True)
class Offered:
    quotes: tuple[TestimonyQuote, ...] = ()
    citations: Mapping[uuid.UUID, Mapping[str, Any]] = field(default_factory=dict)
    sources: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)


QuoteLoader = Callable[[str, str], Awaitable[Offered]]


class ArtisanVoiceBuilder:
    def __init__(self, tools: BuilderTools, *, quotes: QuoteLoader | None = None) -> None:
        self._quotes = quotes or _stored_quotes(tools)

    async def build(self, ask: BuildAsk) -> Built:
        craft = ask.request.craft
        if craft is None:
            return Built()
        offered = await self._quotes(craft.slug, ask.section.discipline)
        limit = QUOTES_BY_DEPTH.get(ask.request.depth or "BASIC", 1)
        chosen = chosen_quotes(offered, _section_stems(ask.blocks), limit=limit)
        block = _block(f"{ask.section.id}.{BLOCK_SUFFIX}", chosen, offered.citations)
        if block is None:
            return Built()
        sources = {sid: offered.sources[sid] for sid in block.cited_source_ids() if sid in offered.sources}
        return Built((block,), {sid: ref for sid, ref in sources.items() if sid not in ask.cited.sources})


def _section_stems(blocks: Iterable[Block]) -> set[str]:
    stems: set[str] = set()
    for block in blocks:
        for sentence in block.cited_sentences():
            stems |= content_stems(sentence.original or sentence.text)
    return stems


def _overlap(quote: TestimonyQuote, stems: set[str]) -> int:
    return len(content_stems(f"{quote.english or ''} {quote.quote}") & stems)


def chosen_quotes(offered: Offered, stems: set[str], *, limit: int) -> list[TestimonyQuote]:
    ranked = sorted(
        offered.quotes,
        key=lambda q: (not q.corroborated_by, -_overlap(q, stems), -q.approved_at.timestamp(), q.item_id),
    )
    chosen: list[TestimonyQuote] = []
    speakers: set[str] = set()
    for quote in ranked:
        if len(chosen) < limit and quote.speaker.line not in speakers:
            chosen.append(quote)
            speakers.add(quote.speaker.line)
    for quote in ranked:
        if len(chosen) < limit and quote not in chosen:
            chosen.append(quote)
    return chosen


def voice_quote_payload(
    quote: TestimonyQuote, citations: Mapping[uuid.UUID, Mapping[str, Any]]
) -> dict[str, Any]:
    speaker = quote.speaker
    return {
        "itemId": quote.item_id,
        "origin": TESTIMONY_ORIGIN,
        "speaker": {
            "name": speaker.name,
            "role": speaker.role,
            "district": speaker.district or None,
            "state": speaker.state or None,
            "line": speaker.line,
        },
        "quote": quote.quote,
        "language": quote.language,
        "english": quote.english,
        "englishSource": quote.english_source if quote.english is not None else None,
        "sourceId": str(quote.source_id),
        "locator": quote.locator,
        "workshop": None,
        "recordedOn": quote.recorded_on,
        "corroboratedBy": [
            dict(citations[claim_id]) for claim_id in quote.corroborated_by if claim_id in citations
        ],
    }


def _valid_quote(payload: dict[str, Any]) -> VoiceQuote | None:
    try:
        return VoiceQuote.model_validate(payload)
    except ValidationError as error:
        logger.warning(
            "testimony quote %s is refused by the artisan_voice model: %s", payload["itemId"], error
        )
        return None


def _block(
    block_id: str, chosen: Sequence[TestimonyQuote], citations: Mapping[uuid.UUID, Mapping[str, Any]]
) -> ArtisanVoiceBlock | None:
    quotes = [valid for quote in chosen if (valid := _valid_quote(voice_quote_payload(quote, citations)))]
    if not quotes:
        return None
    return ArtisanVoiceBlock(id=block_id, kind="artisan_voice", version=2, quotes=quotes, removed=0)


def _stored_quotes(tools: BuilderTools) -> QuoteLoader:
    async def load(craft_slug: str, discipline: str) -> Offered:
        async with tools.sessions() as session:
            craft = await knowledge_view.resolve_craft(session, craft_slug)
            if craft is None:
                return Offered()
            quotes = await approved_quotes(session, craft.id, limit=OFFERED_MAX, disciplines=[discipline])
            wanted = [claim_id for quote in quotes for claim_id in quote.corroborated_by]
            views, sources = await knowledge_view.claims_by_id(session, wanted)
        citations = {cid: views[cid].citations[0] for cid in wanted if cid in views and views[cid].citations}
        refs = {str(q.source_id): q.source for q in quotes}
        refs.update({str(sid): knowledge_view.source_ref(source) for sid, source in sources.items()})
        return Offered(tuple(quotes), citations, refs)

    return load
