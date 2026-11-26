from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.providers.embedding import router_embedder
from app.providers.router import Principal

from .page_refresh_jobs import Background
from .page_refresh_run import refresh_named
from .staged_review_confirm import Confirmed
from .written_vectors import embed_decided

__all__ = ["finish_confirmed"]


async def finish_confirmed(
    session: AsyncSession, confirmed: Confirmed, confirmer: User, background: Background, *, now: datetime
) -> str | None:
    note = await refresh_named(session, confirmed.owners, confirmer, background, now=now)
    embed = router_embedder(Principal(user_id=confirmer.id, role=confirmer.role))
    for decided in confirmed.decided:
        await embed_decided(session, embed, decided)
    return note
