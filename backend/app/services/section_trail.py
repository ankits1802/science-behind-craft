from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.research.evidence_pack import EvidencePack
from app.research.explainer import Block

from .answer_events import CitedClaims
from .answer_trail import TrailLog, stored_key
from .section_deepening import LADDER_KIND

__all__ = ["quote_trail", "stored_sources"]


async def quote_trail(
    trail: TrailLog,
    evidence_ids: Sequence[str],
    blocks: Sequence[Block],
    sources: Mapping[str, Mapping[str, Any]],
) -> None:
    ladder = {sid for block in blocks if block.kind == LADDER_KIND for sid in block.cited_source_ids()}
    cited = dict.fromkeys(source_id for block in blocks for source_id in block.cited_source_ids())
    quoted = [sources[sid] for sid in cited if sid in ladder or trail.knows(stored_key(sid))]
    await trail.quoted(evidence_ids, quoted)


def stored_sources(pack: EvidencePack, stored: CitedClaims) -> list[Mapping[str, Any]]:
    ordered = dict.fromkeys(
        citation["sourceId"]
        for hit in pack.stored.claims
        if hit.claim_id in stored.views
        for citation in stored.views[hit.claim_id].citations
    )
    return [stored.sources[source_id] for source_id in ordered if source_id in stored.sources]
