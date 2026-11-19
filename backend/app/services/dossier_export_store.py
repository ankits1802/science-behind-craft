from __future__ import annotations

import uuid
from collections.abc import Collection
from typing import Any

from pydantic import ValidationError
from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.curation.checks import CheckContext
from app.curation.dossier import CATEGORY_SCOPE
from app.models import (
    Claim,
    ClaimSource,
    Concept,
    Craft,
    CraftCategory,
    CraftGiRecord,
    CraftPrice,
    CraftWorkforce,
    CuratedCategory,
    CuratedCategoryClaim,
    CuratedClaim,
    CuratedCraft,
    KnowledgePiece,
    MediaRef,
    ProcessStage,
    Source,
    StageMaterial,
)
from app.research.blocks import ProseBlock

from .curated_category_index import CuratedCategoryPage
from .curated_index import CuratedPage
from .curation_keys import SUPERSEDED_STATUS
from .curation_writes import stored_values
from .dossier_export_records import (
    CLAIM_COLUMNS,
    GI_COLUMNS,
    MARKER_COLUMNS,
    MEDIA_COLUMNS,
    PRICE_COLUMNS,
    QUOTE_COLUMNS,
    SOURCE_COLUMNS,
    STAGE_COLUMNS,
    USE_COLUMNS,
    WORKFORCE_COLUMNS,
    StoredCuration,
    StoredMarket,
    piece_sentences,
)

__all__ = ["FAMILY_SCOPE", "stored_category", "stored_craft"]

CRAFT_SCOPE = "CRAFT"
FAMILY_SCOPE = "FAMILY"
SUBJECT_COLUMNS = ("id", "originRef")
PIECE_COLUMNS = ("id", "payload")


async def stored_craft(session: AsyncSession, slug: str, context: CheckContext) -> StoredCuration:
    scope = context.crafts.get(slug)
    if scope is None:
        raise InvalidInput(f"{slug} is not a craft of the master list or the portal craft register")
    craft = await session.scalar(select(Craft).where(Craft.slug == slug))
    stored = (
        None
        if craft is None
        else await session.scalar(select(CuratedCraft.page).where(CuratedCraft.craftId == craft.id))
    )
    if craft is None or stored is None:
        raise InvalidInput(f"craft {slug} has no curated dossier in the database")
    page = _page(CuratedPage, stored, slug)
    claim_ids = list(page.claim_order) or await _current(
        session, CuratedClaim.claimId, CuratedClaim.craftId == craft.id
    )
    stage_ids = [stage.stage_id for stage in page.stages]
    return StoredCuration(
        **await _evidence(session, slug, page, (claim_ids, CuratedClaim)),
        scope=FAMILY_SCOPE if scope.family else CRAFT_SCOPE,
        page=page,
        claim_order=tuple(page.claim_order),
        stages=await stored_values(session, ProcessStage, stage_ids, STAGE_COLUMNS),
        uses=await _where(session, StageMaterial, StageMaterial.stageId.in_(stage_ids), USE_COLUMNS),
        market=await _market(session, craft.id),
    )


async def stored_category(session: AsyncSession, slug: str) -> StoredCuration:
    category = await session.scalar(select(CraftCategory).where(CraftCategory.slug == slug))
    stored = (
        None
        if category is None
        else await session.scalar(
            select(CuratedCategory.page).where(CuratedCategory.categoryId == category.id)
        )
    )
    if category is None or stored is None:
        raise InvalidInput(f"category {slug} has no curated dossier in the database")
    page = _page(CuratedCategoryPage, stored, slug)
    owned = CuratedCategoryClaim.categoryId == category.id
    claim_ids = await _current(session, CuratedCategoryClaim.claimId, owned)
    return StoredCuration(
        **await _evidence(session, slug, page, (claim_ids, CuratedCategoryClaim)),
        scope=CATEGORY_SCOPE,
        page=page,
    )


def _page[P: (CuratedPage, CuratedCategoryPage)](model: type[P], stored: dict[str, Any], slug: str) -> P:
    try:
        return model.model_validate(stored)
    except ValidationError as error:
        raise InvalidInput(
            f"the stored page index of {slug} no longer meets its model; import it again"
        ) from error


async def _current(session: AsyncSession, marker: Any, owned: ColumnElement[bool]) -> list[uuid.UUID]:
    marked = select(marker).where(owned)
    rows = await session.scalars(
        select(Claim.id).where(Claim.id.in_(marked), Claim.status != SUPERSEDED_STATUS)
    )
    return list(rows.all())


async def _evidence(
    session: AsyncSession,
    slug: str,
    page: CuratedPage | CuratedCategoryPage,
    marked: tuple[list[uuid.UUID], Any],
) -> dict[str, Any]:
    claim_ids, marker = marked
    claims = await stored_values(session, Claim, claim_ids, CLAIM_COLUMNS)
    quotes = await _where(session, ClaimSource, ClaimSource.claimId.in_(claim_ids), QUOTE_COLUMNS)
    concepts = await stored_values(
        session, Concept, {row["subjectId"] for row in claims.values()}, SUBJECT_COLUMNS
    )
    pieces = await stored_values(session, KnowledgePiece, list(page.piece_ids().values()), PIECE_COLUMNS)
    return {
        "slug": slug,
        "claims": claims,
        "markers": await stored_values(session, marker, claim_ids, MARKER_COLUMNS, key="claimId"),
        "quotes": quotes,
        "sources": await stored_values(session, Source, {row["sourceId"] for row in quotes}, SOURCE_COLUMNS),
        "subjects": {concept_id: row["originRef"] for concept_id, row in concepts.items()},
        "media": await stored_values(
            session, MediaRef, [p.media_ref_id for p in page.pictures], MEDIA_COLUMNS
        ),
        "sentences": {
            piece_id: piece_sentences(ProseBlock.model_validate(row["payload"]))
            for piece_id, row in pieces.items()
        },
    }


async def _market(session: AsyncSession, craft_id: uuid.UUID) -> StoredMarket:
    gi = await _where(session, CraftGiRecord, CraftGiRecord.craftId == craft_id, GI_COLUMNS)
    return StoredMarket(
        gi=gi[0] if gi else None,
        prices=await _where(session, CraftPrice, CraftPrice.craftId == craft_id, PRICE_COLUMNS),
        workforce=await _where(
            session, CraftWorkforce, CraftWorkforce.craftId == craft_id, WORKFORCE_COLUMNS
        ),
    )


async def _where(
    session: AsyncSession, model: Any, condition: ColumnElement[bool], columns: Collection[str]
) -> tuple[dict[str, Any], ...]:
    table = model.__table__
    rows = await session.execute(select(*(table.c[column] for column in columns)).where(condition))
    return tuple(dict(row) for row in rows.mappings())
