from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.research.explainer import Explainer, explainer_blocks
from app.research.explainer_versions import ExplainerVersionDocument
from app.research.retrieval import chunk_acls_for

from . import knowledge_view
from .field_voices_readback import Withdrawn, without_withdrawn
from .visible_claims import stored_uuids

__all__ = ["PUBLIC_READING_ACLS", "closed_citations", "public_explainer", "public_version"]

PUBLIC_READING_ACLS: tuple[str, ...] = chunk_acls_for(None)


async def public_version(
    session: AsyncSession, document: ExplainerVersionDocument
) -> ExplainerVersionDocument | None:
    shown = await public_explainer(session, document.explainer)
    return None if shown is None else document.model_copy(update={"explainer": shown})


async def public_explainer(session: AsyncSession, explainer: Explainer) -> Explainer | None:
    closed = await closed_citations(session, explainer)
    return without_withdrawn(explainer, Withdrawn(citations=closed))


async def closed_citations(session: AsyncSession, explainer: Explainer) -> frozenset[tuple[str, str]]:
    cited = {
        (citation.claim_id, citation.source_id)
        for block in explainer_blocks(explainer)
        for citation in block.citations()
    }
    claims = stored_uuids(dict.fromkeys(claim for claim, _ in cited))
    views, _sources = await knowledge_view.claims_by_id(session, claims, acls=PUBLIC_READING_ACLS)
    readable = {(str(view.id), cite["sourceId"]) for view in views.values() for cite in view.citations}
    return frozenset(cited - readable)
