from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Claim, ClaimSource, Concept, Craft, CraftGiRecord, CraftPrice, Source
from app.research.citations import SourceRef
from app.research.crafts import CraftRef
from app.research.gi_registry import MARKET_PREFILTER_WORDS, REGISTRY_SOURCE_KINDS, GiFields

from . import knowledge_view
from .knowledge_view import ClaimView
from .learning_facts import source_refs

__all__ = [
    "MARKET_CANDIDATES_MAX",
    "GiRecordOffer",
    "MarketOffers",
    "PriceOffer",
    "market_offers",
]

MARKET_CANDIDATES_MAX = 80
CONCEPT_SUBJECT = "CONCEPT"


@dataclass(frozen=True)
class GiRecordOffer:
    fields: GiFields
    claim_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class PriceOffer:
    claim_id: uuid.UUID
    priced_on: str | None
    place: str | None
    district_lgd: int | None


@dataclass(frozen=True)
class MarketOffers:
    craft: CraftRef
    record: GiRecordOffer | None = None
    prices: tuple[PriceOffer, ...] = ()
    candidates: tuple[uuid.UUID, ...] = ()
    views: Mapping[uuid.UUID, ClaimView] = field(default_factory=dict)
    sources: Mapping[str, SourceRef] = field(default_factory=dict)


async def market_offers(session: AsyncSession, crafts: Sequence[CraftRef]) -> list[MarketOffers]:
    found: list[MarketOffers] = []
    for ref in crafts:
        craft = await knowledge_view.resolve_craft(session, ref.slug)
        if craft is not None:
            found.append(await _craft_offers(session, craft))
    return found


async def _craft_offers(session: AsyncSession, craft: Craft) -> MarketOffers:
    record = await _gi_record(session, craft.id)
    prices = await _prices(session, craft.id)
    candidates = await _registry_claims(session, craft.id)
    wanted = [*(record.claim_ids if record else ()), *(price.claim_id for price in prices), *candidates]
    views, sources = await knowledge_view.claims_by_id(session, wanted)
    return MarketOffers(
        craft=CraftRef.model_validate(knowledge_view.craft_ref(craft)),
        record=record,
        prices=prices,
        candidates=candidates,
        views=views,
        sources=source_refs(sources),
    )


async def _gi_record(session: AsyncSession, craft_id: uuid.UUID) -> GiRecordOffer | None:
    row = await session.get(CraftGiRecord, craft_id)
    if row is None:
        return None
    fields = GiFields(
        application_number=row.applicationNumber,
        certificate_number=row.certificateNumber,
        filed_on=row.filedOn,
        registered_on=row.registeredOn,
        journal_issue=row.journalIssue,
        proprietors=tuple(row.proprietors),
        authorised_user_count=row.authorisedUserCount,
    )
    return GiRecordOffer(fields=fields, claim_ids=tuple(row.claimIds))


async def _prices(session: AsyncSession, craft_id: uuid.UUID) -> tuple[PriceOffer, ...]:
    rows = await session.execute(
        select(CraftPrice.claimId, CraftPrice.pricedOn, CraftPrice.placeName, CraftPrice.districtLgd)
        .where(CraftPrice.craftId == craft_id)
        .order_by(CraftPrice.pricedOn.desc(), CraftPrice.claimId, CraftPrice.placeName)
    )
    return tuple(
        PriceOffer(
            claim_id=row.claimId, priced_on=row.pricedOn, place=row.placeName, district_lgd=row.districtLgd
        )
        for row in rows.all()
    )


async def _registry_claims(session: AsyncSession, craft_id: uuid.UUID) -> tuple[uuid.UUID, ...]:
    owned = select(Concept.id).where(Concept.craftId == craft_id)
    statement = (
        select(Claim.id)
        .join(ClaimSource, ClaimSource.claimId == Claim.id)
        .join(Source, Source.id == ClaimSource.sourceId)
        .where(
            Claim.subjectType == CONCEPT_SUBJECT,
            Claim.subjectId.in_(owned),
            Source.kind.in_(REGISTRY_SOURCE_KINDS),
            or_(*(Claim.text.ilike(f"%{word}%") for word in MARKET_PREFILTER_WORDS)),
        )
        .distinct()
        .order_by(Claim.id)
        .limit(MARKET_CANDIDATES_MAX)
    )
    return tuple((await session.scalars(statement)).all())
