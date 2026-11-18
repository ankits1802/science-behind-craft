from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ArtisanContribution
from app.research.testimony import screens_for

from .reader_profiles import held_back_name_terms

__all__ = ["SCREENED_STATUSES", "contribution_screens", "rescreen_contributions"]

SCREENED_STATUSES = ("PENDING", "APPROVED")


def contribution_screens(contribution: ArtisanContribution, terms: frozenset[str]) -> list[str]:
    return screens_for([contribution.quote, contribution.english, contribution.claimText], terms)


async def rescreen_contributions(session: AsyncSession, user_id: uuid.UUID) -> int:
    terms = await held_back_name_terms(session, user_id)
    rows = await session.scalars(
        select(ArtisanContribution)
        .where(ArtisanContribution.userId == user_id, ArtisanContribution.status.in_(SCREENED_STATUSES))
        .with_for_update()
    )
    held_back = 0
    for contribution in rows:
        screens = contribution_screens(contribution, terms)
        if screens != list(contribution.screens or []):
            contribution.screens = screens
            contribution.version += 1
        held_back += int(bool(screens) and contribution.status == "APPROVED")
    return held_back
