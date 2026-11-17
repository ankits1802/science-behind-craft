from __future__ import annotations

import uuid

from app.research.composition import (
    ComposeCandidate,
    ComposeFocus,
    ComposeRequest,
    ResearchSummary,
    SearchedQuery,
)
from app.research.evidence import SourceDocument
from app.research.evidence_pack import EvidencePack
from app.research.retrieval import ClaimHit
from app.research.vocabulary import LABEL_LEVELS

__all__ = [
    "EVIDENCE_LEVEL",
    "WHOLE_TEXT_MAX_CHARS",
    "claim_candidate",
    "compose_request",
    "document_candidate",
    "research_summary",
    "stored_claim_candidate",
]

WHOLE_TEXT_MAX_CHARS = 4000
EVIDENCE_LEVEL = LABEL_LEVELS["QUOTED"]
LABEL_MAX_CHARS = 300


def compose_request(
    pack: EvidencePack, question: str, *, focus: ComposeFocus | None = None
) -> ComposeRequest:
    claims = [claim_candidate(hit) for hit in pack.stored.claims]
    documents = [candidate for doc in pack.documents if (candidate := document_candidate(doc)) is not None]
    return ComposeRequest(
        question=question,
        craft=pack.plan.craft,
        candidates=[*claims, *documents],
        searched=research_summary(pack),
        focus=focus,
    )


def claim_candidate(hit: ClaimHit) -> ComposeCandidate:
    return stored_claim_candidate(hit.claim_id, hit.text, hit.level)


def stored_claim_candidate(claim_id: uuid.UUID, text: str, level: str) -> ComposeCandidate:
    return ComposeCandidate(
        id=str(claim_id), kind="CLAIM", text=text, source_label=f"stored claim, {level.lower()}", level=level
    )


def document_candidate(document: SourceDocument) -> ComposeCandidate | None:
    passages = _passages(document)
    if not passages:
        return None
    return ComposeCandidate(
        id=document.item.id,
        kind="EVIDENCE",
        text=passages[0],
        quotes=passages[1:],
        source_label=_source_label(document),
        level=EVIDENCE_LEVEL,
    )


def research_summary(pack: EvidencePack, *more: EvidencePack) -> ResearchSummary:
    packs = (pack, *more)
    found_by = {name for each in packs for entry in each.evidence for name in entry.found_by}
    failed = {failure.service for each in packs for failure in each.failures}
    queries = (SearchedQuery(tier=q.tier, text=q.query.text) for each in packs for q in each.plan.queries)
    return ResearchSummary(
        craft=pack.plan.craft,
        mode=pack.plan.mode,
        stored_claims=len({hit.claim_id for each in packs for hit in each.stored.claims}),
        stored_passages=len({hit.chunk_id for each in packs for hit in each.stored.chunks}),
        queries=tuple(dict.fromkeys(queries)),
        services=tuple(sorted(found_by | failed)),
        evidence_found=len({entry.item.id for each in packs for entry in each.evidence}),
        documents_read=len({document.item.id for each in packs for document in each.documents}),
        failures=sum(len(each.failures) for each in packs),
    )


def _passages(document: SourceDocument) -> list[str]:
    if len(document.text) <= WHOLE_TEXT_MAX_CHARS:
        return [document.text]
    return list(dict.fromkeys(quote.text for quote in document.item.quotes))


def _source_label(document: SourceDocument) -> str:
    item = document.item
    year = item.published[:4] if item.published else "undated"
    where = item.publisher or item.adapter
    label = f"{item.title} ({where}, {year}, {document.content.lower().replace('_', ' ')})"
    return label[:LABEL_MAX_CHARS]
