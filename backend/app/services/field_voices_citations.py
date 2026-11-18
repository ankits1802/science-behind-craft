from __future__ import annotations

import hashlib
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.composer.candidates import field_evidence_id
from app.models import Source
from app.research.evidence import EvidenceItem, SourceDocument
from app.research.evidence_pack import EvidencePack
from app.research.field_voices import FIELD_SOURCE_KIND, FIELD_VOICES_ADAPTER
from app.research.retrieval import ChunkHit

__all__ = ["FIELD_TIER", "field_documents", "field_hits", "writes_back"]

FIELD_TIER = "T3"
FIELD_TRUST = "A"
EXCERPT = "EXCERPT"


def field_hits(pack: EvidencePack) -> list[ChunkHit]:
    return [hit for hit in pack.stored.chunks if hit.source_kind == FIELD_SOURCE_KIND]


def writes_back(pack: EvidencePack) -> bool:
    return bool(pack.documents) or bool(field_hits(pack))


async def field_documents(session: AsyncSession, pack: EvidencePack) -> Mapping[str, SourceDocument]:
    hits = field_hits(pack)
    if not hits:
        return {}
    sources = {
        row.id: row
        for row in await session.scalars(
            select(Source).where(
                Source.id.in_({hit.source_id for hit in hits}), Source.kind == FIELD_SOURCE_KIND
            )
        )
    }
    documents: dict[str, SourceDocument] = {}
    for hit in hits:
        source = sources.get(hit.source_id)
        if source is None or not (source.url or "").startswith("https://") or source.retrievedAt is None:
            continue
        document = _document(hit, source)
        documents[document.item.id] = document
    return documents


def _document(hit: ChunkHit, source: Source) -> SourceDocument:
    item = EvidenceItem(
        id=field_evidence_id(hit),
        adapter=FIELD_VOICES_ADAPTER,
        tier=FIELD_TIER,
        source_type=FIELD_SOURCE_KIND,
        url=source.url or "",
        title=source.title,
        authors=[str(author) for author in source.authors],
        published=str(source.year) if source.year else None,
        retrieved_at=source.retrievedAt,
        attribution=source.attribution,
        publisher=source.publisher,
        trust=FIELD_TRUST,
    )
    digest = hashlib.sha256(hit.text.encode("utf-8")).hexdigest()
    return SourceDocument(item=item, text=hit.text, text_sha256=digest, truncated=False, content=EXCERPT)
