from __future__ import annotations

import uuid
from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.district_register import load_district_codes
from app.models import ClaimSource, Craft, CraftLocation
from app.research.stated_quantities import UNIT_WORDS

from . import knowledge_view
from .builder_evidence import known_fact
from .learning_facts import source_refs
from .measure_regions import CraftPlaces, RegionalFactors, chosen_factors, claim_factors, district_states
from .region_records import located_places

__all__ = ["CONVERSION_CLAIMS_MAX", "craft_places", "regional_factors"]

CONVERSION_CLAIMS_MAX = 60


async def regional_factors(session: AsyncSession, craft_slug: str, units: Collection[str]) -> RegionalFactors:
    craft = await knowledge_view.resolve_craft(session, craft_slug)
    if craft is None or not units:
        return RegionalFactors()
    places = await craft_places(session, craft)
    if not places.states:
        return RegionalFactors()
    views, sources = await knowledge_view.claims_by_id(session, await _stating_claims(session, units))
    facts = [fact for view in views.values() if (fact := known_fact(view)) is not None]
    found = (factor for fact in facts for factor in claim_factors(fact, units))
    return RegionalFactors(factors=chosen_factors(found, places), sources=source_refs(sources))


async def craft_places(session: AsyncSession, craft: Craft) -> CraftPlaces:
    located = located_places(CraftLocation.craftId == craft.id)
    rows = (await session.execute(select(located.c.stateLgd, located.c.located_lgd))).all()
    districts = {row.located_lgd for row in rows if row.located_lgd is not None}
    of_districts = {district_states()[lgd] for lgd in districts if lgd in district_states()}
    states = {row.stateLgd for row in rows if row.stateLgd is not None} | of_districts
    codes = load_district_codes()
    practised = {codes.state_lgd(name.strip()) for name in craft.stateOfPractice or ()}
    return CraftPlaces(states=frozenset(states | (practised - {None})), districts=frozenset(districts))


async def _stating_claims(session: AsyncSession, units: Collection[str]) -> list[uuid.UUID]:
    words = sorted(word for word, unit in UNIT_WORDS.items() if unit in units and word.isalpha())
    if not words:
        return []
    statement = (
        select(ClaimSource.claimId)
        .where(ClaimSource.quote.op("~*")(r"\m(" + "|".join(words) + r")\M"))
        .distinct()
        .order_by(ClaimSource.claimId)
        .limit(CONVERSION_CLAIMS_MAX)
    )
    return list((await session.scalars(statement)).all())
