from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Claim,
    Concept,
    Craft,
    CuratedClaim,
    CuratedCraft,
    MediaRef as MediaRefRow,
    MediaRefClaim,
    Term,
    TermCraft,
)
from app.research.citations import SourceRef
from app.research.craft_page import PageCraft
from app.research.craft_page_context import PageRelative
from app.research.field_voices import FIELD_PHOTOS_SHOWN, FIELD_VOICES_SHOWN
from app.research.image_relevance import PictureContext
from app.research.knowledge_pieces import KnowledgePiece
from app.research.media_refs import MediaRef
from app.research.retrieval import OPEN_CHUNK_ACLS
from app.science.records import ProcessRecords

from . import knowledge_view
from .claim_holds import unheld_views
from .contributed_pictures import ContributedRecord, approved_pictures
from .craft_ai_media import AiMediaRecord, shared_ai_media
from .craft_page_family import family_names, family_place, family_relatives, reader_name
from .craft_page_market import MarketFacts, market_facts
from .craft_page_offers import PageOffers, page_offers
from .craft_picture_context import picture_context_of
from .craft_process import process_records
from .curated_index import CuratedPage, stored_curated_page
from .field_voices_view import FieldVoicesPart, voices_part
from .knowledge_view import ClaimView
from .media_ref_store import StoredPicture, field_media, stored_media_ref, stored_media_refs
from .piece_lookup import stored_pieces
from .served_pictures import searched_text_link, served_picture
from .term_glossary import glossary_entries

__all__ = [
    "PAGE_MODE",
    "PICTURES_SHOWN_MAX",
    "ClaimFacts",
    "CraftPageRecords",
    "PictureRecord",
    "TermRecord",
    "craft_page_records",
    "page_craft",
    "stored_page_pictures",
]

PAGE_MODE = "HYBRID"
PICTURES_SHOWN_MAX = 6


@dataclass(frozen=True)
class ClaimFacts:
    origin: str
    sources_differ: bool
    discipline: str | None
    concept_name: str | None
    concept_type: str | None


@dataclass(frozen=True)
class TermRecord:
    key: str
    label: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class PictureRecord:
    media: MediaRef
    claim_ids: tuple[uuid.UUID, ...]
    may_lead: bool


@dataclass(frozen=True)
class CraftPageRecords:
    craft: PageCraft
    curated: CuratedPage | None
    views: tuple[ClaimView, ...]
    facts: Mapping[uuid.UUID, ClaimFacts]
    sources: Mapping[str, SourceRef]
    process: ProcessRecords
    pieces: Mapping[uuid.UUID, KnowledgePiece] = field(default_factory=dict)
    media: Mapping[uuid.UUID, MediaRef] = field(default_factory=dict)
    pictures: tuple[PictureRecord, ...] = ()
    terms: tuple[TermRecord, ...] = ()
    market: MarketFacts = field(default_factory=MarketFacts)
    relatives: tuple[PageRelative, ...] = ()
    offers: PageOffers = field(default_factory=PageOffers)
    catch_all: bool = False
    field_voices: FieldVoicesPart = field(default_factory=FieldVoicesPart)
    contributed: tuple[ContributedRecord, ...] = ()
    ai_media: tuple[AiMediaRecord, ...] = ()


def page_craft(craft: Craft, names: tuple[str | None, str | None]) -> PageCraft:
    category, sub_category = names
    place = family_place(category, sub_category)
    return PageCraft(
        id=craft.id,
        slug=craft.slug,
        name=craft.name,
        path=f"/crafts/{craft.slug}",
        display_name=reader_name(craft.slug, craft.name, catch_all=bool(craft.isCatchAll), kind=place.kind),
        local_name=craft.localName,
        local_names=[],
        category_name=category or craft.category,
        sub_category_name=sub_category,
        family_label=place.family.label if place.family else None,
        kind_label=place.kind.label if place.kind else None,
        gi_status=craft.giStatus,
        state_of_practice=list(craft.stateOfPractice or []),
        state_of_origin=list(craft.stateOfOrigin or []),
    )


async def craft_page_records(
    session: AsyncSession, craft: Craft, *, acls: Sequence[str] = OPEN_CHUNK_ACLS
) -> CraftPageRecords:
    curated = await _curated(session, craft.id)
    views, sources = await knowledge_view.claims_for(session, craft, mode=PAGE_MODE, acls=acls)
    views = await unheld_views(session, views)
    records = CraftPageRecords(
        craft=page_craft(craft, await family_names(session, craft) or (None, None)),
        curated=curated,
        views=tuple(views),
        facts=await _facts(session, views),
        sources={
            str(key): SourceRef.model_validate(knowledge_view.source_ref(row)) for key, row in sources.items()
        },
        process=await process_records(session, craft, acls=acls),
        market=await market_facts(session, craft.id),
        relatives=await family_relatives(session, craft, mode=PAGE_MODE),
        offers=await page_offers(session, craft),
        catch_all=bool(craft.isCatchAll),
        field_voices=await voices_part(
            session, craft.id, voices=FIELD_VOICES_SHOWN, photos=FIELD_PHOTOS_SHOWN
        ),
        contributed=await approved_pictures(session, craft.id),
        ai_media=await shared_ai_media(session, craft.id),
    )
    if curated is None:
        return await _stored_extras(session, craft, records)
    pieces = await stored_pieces(session, list(curated.piece_ids().values()))
    media = await stored_media_refs(session, [picture.media_ref_id for picture in curated.pictures])
    return replace(records, pieces=pieces, media=media)


async def _curated(session: AsyncSession, craft_id: uuid.UUID) -> CuratedPage | None:
    page = await session.scalar(select(CuratedCraft.page).where(CuratedCraft.craftId == craft_id))
    return stored_curated_page(craft_id, page)


async def _facts(session: AsyncSession, views: Sequence[ClaimView]) -> dict[uuid.UUID, ClaimFacts]:
    if not views:
        return {}
    claims = (
        await session.execute(
            select(Claim.id, Claim.origin, Claim.sourcesDiffer, CuratedClaim.discipline)
            .outerjoin(CuratedClaim, CuratedClaim.claimId == Claim.id)
            .where(Claim.id.in_([view.id for view in views]))
        )
    ).all()
    concept_ids = {view.concept_id for view in views if view.concept_id is not None}
    concepts = {
        row.id: row
        for row in (
            await session.execute(
                select(Concept.id, Concept.name, Concept.type).where(Concept.id.in_(concept_ids))
            )
        ).all()
    }
    by_claim = {row.id: row for row in claims}
    return {view.id: _fact(by_claim[view.id], concepts.get(view.concept_id)) for view in views}


def _fact(claim: Any, concept: Any) -> ClaimFacts:
    return ClaimFacts(
        origin=claim.origin,
        sources_differ=claim.sourcesDiffer,
        discipline=claim.discipline,
        concept_name=concept.name if concept else None,
        concept_type=concept.type if concept else None,
    )


async def _stored_extras(session: AsyncSession, craft: Craft, records: CraftPageRecords) -> CraftPageRecords:
    claim_ids = [view.id for view in records.views]
    links = await session.execute(
        select(MediaRefRow, MediaRefClaim.claimId, MediaRefClaim.relevance)
        .join(MediaRefClaim, MediaRefClaim.mediaRefId == MediaRefRow.id)
        .where(MediaRefClaim.claimId.in_(claim_ids), MediaRefRow.id.not_in(field_media()))
        .order_by(MediaRefRow.id, MediaRefClaim.claimId)
    )
    stored = [
        StoredPicture(stored_media_ref(row), claim_id, relevance)
        for row, claim_id, relevance in links.tuples()
    ]
    pictures = stored_page_pictures(stored, await picture_context_of(session, craft))
    return replace(records, pictures=pictures, terms=await _terms(session, craft))


def stored_page_pictures(
    stored: Sequence[StoredPicture], context: PictureContext
) -> tuple[PictureRecord, ...]:
    linked: dict[uuid.UUID, list[StoredPicture]] = {}
    for picture in stored:
        if served_picture(picture, context):
            linked.setdefault(picture.media.id, []).append(picture)
    return tuple(
        PictureRecord(
            links[0].media,
            tuple(link.claim_id for link in links),
            may_lead=not any(searched_text_link(link) for link in links),
        )
        for links in list(linked.values())[:PICTURES_SHOWN_MAX]
    )


async def _terms(session: AsyncSession, craft: Craft) -> tuple[TermRecord, ...]:
    keys = {entry.key for entry in await glossary_entries(session, [craft.id])}
    linked = select(TermCraft.termId).where(TermCraft.craftId == craft.id)
    rows = await session.scalars(
        select(Term).where(Term.id.in_(linked), Term.key.in_(keys)).order_by(Term.key)
    )
    return tuple(
        TermRecord(row.key, row.label, tuple(dict.fromkeys([*row.aliases, *row.localNames]))) for row in rows
    )
