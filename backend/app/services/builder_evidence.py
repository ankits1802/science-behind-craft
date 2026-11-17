from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from app.research.blocks import ExplainerSentence
from app.research.citations import Citation, SourceRef
from app.research.explainer import Block
from app.research.vocabulary import FACT_LEVELS
from app.science.records import KnownClaim

from .answer_events import CitedClaims
from .builder_interface import SourceRefs
from .knowledge_view import ClaimView

__all__ = ["fact_sentence", "known_claim", "known_fact", "section_facts", "sources_beyond"]


def section_facts(
    blocks: Sequence[Block], cited: CitedClaims, *, limit: int | None = None
) -> list[KnownClaim]:
    ordered = dict.fromkeys(citation.claim_id for block in blocks for citation in block.citations())
    found: list[KnownClaim] = []
    for claim_id in ordered:
        view = cited.views.get(uuid.UUID(claim_id))
        fact = known_fact(view) if view is not None else None
        if fact is None:
            continue
        found.append(fact)
        if limit is not None and len(found) == limit:
            break
    return found


def known_fact(view: ClaimView) -> KnownClaim | None:
    return known_claim(view) if view.level in FACT_LEVELS else None


def known_claim(view: ClaimView) -> KnownClaim | None:
    if not view.citations:
        return None
    citations = tuple(Citation.model_validate(citation) for citation in view.citations)
    return KnownClaim(view.id, view.text, view.level, citations)


def fact_sentence(claim: KnownClaim, sentence_id: str) -> ExplainerSentence:
    return ExplainerSentence(
        id=sentence_id, text=claim.text, level=claim.level, citations=list(claim.citations), terms=[]
    )


def sources_beyond(blocks: Iterable[Block], known: Mapping[str, SourceRef], cited: CitedClaims) -> SourceRefs:
    found: dict[str, Mapping[str, Any]] = {}
    for block in blocks:
        for source_id in block.cited_source_ids():
            if source_id in cited.sources or source_id in found:
                continue
            ref = known.get(source_id)
            if ref is not None:
                found[source_id] = ref.model_dump(mode="json", by_alias=True)
    return found
