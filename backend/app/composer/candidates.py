from __future__ import annotations

import uuid

from app.research.composition import ComposeCandidate, ComposeRequest, ResearchSummary, SearchedQuery
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


def compose_request(pack: EvidencePack, question: str) -> ComposeRequest:
    claims = [claim_candidate(hit) for hit in pack.stored.claims]
    documents = [candidate for doc in pack.documents if (candidate := document_candidate(doc)) is not None]
    return ComposeRequest(
        question=question,
        craft=pack.plan.craft,
        candidates=[*claims, *documents],
        searched=research_summary(pack),
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


def research_summary(pack: EvidencePack) -> ResearchSummary:
    found_by = {name for entry in pack.evidence for name in entry.found_by}
    failed = {failure.service for failure in pack.failures}
    return ResearchSummary(
        craft=pack.plan.craft,
        mode=pack.plan.mode,
        stored_claims=len(pack.stored.claims),
        stored_passages=len(pack.stored.chunks),
        queries=tuple(SearchedQuery(tier=q.tier, text=q.query.text) for q in pack.plan.queries),
        services=tuple(sorted(found_by | failed)),
        evidence_found=len(pack.evidence),
        documents_read=len(pack.documents),
        failures=len(pack.failures),
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
