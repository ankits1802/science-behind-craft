from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.research.explainer import Explainer, explainer_blocks
from app.research.retrieval import EVERY_CHUNK_ACLS

from . import knowledge_view

__all__ = ["stored_uuids", "visible_claim_ids"]


async def visible_claim_ids(
    session: AsyncSession, explainer: Explainer, *, acls: Sequence[str] = EVERY_CHUNK_ACLS
) -> frozenset[str]:
    cited = dict.fromkeys(c.claim_id for block in explainer_blocks(explainer) for c in block.citations())
    visible, _sources = await knowledge_view.claims_by_id(session, stored_uuids(cited), acls=acls)
    return frozenset(str(claim_id) for claim_id in visible)


def stored_uuids(values: Iterable[str]) -> list[uuid.UUID]:
    found: list[uuid.UUID] = []
    for value in values:
        try:
            found.append(uuid.UUID(value))
        except ValueError:
            continue
    return found
