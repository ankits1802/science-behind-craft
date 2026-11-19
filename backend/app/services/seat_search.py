from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field

from app.research.crafts import QUESTION_MAX_CHARS
from app.research.expert_panel import SeatBrief
from app.research.retrieval import SIGNED_IN_CHUNK_ACLS, KnowledgeHits, KnowledgeQuery
from app.research.sections import DISCIPLINE_FIELDS
from app.research.vocabulary import FACT_LEVELS

from . import knowledge_view
from .answer_events import CitedClaims, cited_claims
from .builder_interface import BuildAsk, BuilderTools
from .knowledge_view import ClaimView

__all__ = [
    "SEAT_CLAIMS_MAX",
    "SEAT_READING_ACLS",
    "SEAT_SEARCH_LIMIT",
    "SeatEvidence",
    "SeatSearch",
    "seat_findings",
    "seat_query",
    "stored_seat_search",
]

SEAT_SEARCH_LIMIT = 12
SEAT_CLAIMS_MAX = 6
SEAT_READING_ACLS = SIGNED_IN_CHUNK_ACLS


@dataclass(frozen=True)
class SeatEvidence:
    found: Mapping[str, tuple[ClaimView, ...]] = field(default_factory=dict)
    cited: CitedClaims = field(default_factory=CitedClaims)


SeatSearch = Callable[[BuildAsk, Sequence[SeatBrief], Collection[str]], Awaitable[SeatEvidence]]


def seat_query(ask: BuildAsk, brief: SeatBrief) -> KnowledgeQuery:
    craft = ask.request.craft
    words = [
        ask.request.english_question or ask.request.question,
        craft.name if craft else "",
        brief.label,
        *(DISCIPLINE_FIELDS[discipline] for discipline in brief.fields),
    ]
    text = " ".join(word for word in words if word)[:QUESTION_MAX_CHARS]
    return KnowledgeQuery(
        craft_slug=craft.slug if craft else None,
        text=text,
        mode=ask.request.mode,
        fields=brief.fields,
        limit=SEAT_SEARCH_LIMIT,
    )


def seat_findings(
    briefs: Sequence[SeatBrief], hits: Sequence[KnowledgeHits], cited: CitedClaims, shown: Collection[str]
) -> dict[str, tuple[ClaimView, ...]]:
    return {brief.seat: _found(brief, found, cited, shown) for brief, found in zip(briefs, hits, strict=True)}


def stored_seat_search(tools: BuilderTools) -> SeatSearch:
    async def search(ask: BuildAsk, briefs: Sequence[SeatBrief], shown: Collection[str]) -> SeatEvidence:
        retriever = tools.retriever
        if retriever is None or tools.sessions is None or not briefs:
            return SeatEvidence()
        hits = await asyncio.gather(*(retriever.search(seat_query(ask, brief)) for brief in briefs))
        wanted = [hit.claim_id for found in hits for hit in found.claims]
        async with tools.sessions() as session:
            views, sources = await knowledge_view.claims_by_id(session, wanted, acls=SEAT_READING_ACLS)
        cited = cited_claims(list(views.values()), sources)
        return SeatEvidence(seat_findings(briefs, hits, cited, shown), cited)

    return search


def _found(
    brief: SeatBrief, hits: KnowledgeHits, cited: CitedClaims, shown: Collection[str]
) -> tuple[ClaimView, ...]:
    kinds = set(brief.source_kinds)
    kept: dict[uuid.UUID, ClaimView] = {}
    for hit in hits.claims:
        view = cited.views.get(hit.claim_id)
        if view is None or view.id in kept or str(view.id) in shown or view.level not in FACT_LEVELS:
            continue
        if _source_kinds(view, cited) & kinds:
            kept[view.id] = view
        if len(kept) == SEAT_CLAIMS_MAX:
            break
    return tuple(kept.values())


def _source_kinds(view: ClaimView, cited: CitedClaims) -> set[str]:
    refs = (cited.sources.get(str(citation["sourceId"])) for citation in view.citations)
    return {str(ref["kind"]) for ref in refs if ref is not None and ref.get("kind")}
