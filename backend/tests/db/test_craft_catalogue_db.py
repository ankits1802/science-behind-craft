import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.geo.places import DISTRICT_PRECISIONS
from app.models import Craft, CraftLocation
from app.research.craft_catalogue import CraftCatalogue
from app.services.craft_catalogue import load_catalogue
from app.services.curation_import import import_curation

from ..curation.import_support import AJRAKH, raw
from .test_curation_import_db import ajrakh_id, imported, session

pytestmark = pytest.mark.db

__all__ = ["session"]


async def test_the_catalogue_carries_the_curated_depth_hero_and_gi_year(session: AsyncSession) -> None:
    imported(await import_curation(session), AJRAKH)
    catalogue = CraftCatalogue.model_validate(await load_catalogue(session))
    ajrakh = next(row for row in catalogue.crafts if row.slug == AJRAKH)
    dossier = raw(AJRAKH)
    located = await session.scalar(
        select(func.count())
        .select_from(CraftLocation)
        .where(
            CraftLocation.craftId == await ajrakh_id(session),
            CraftLocation.precision.in_(DISTRICT_PRECISIONS),
        )
    )
    assert ajrakh.depth.coverage == dossier["coverage"]
    assert ajrakh.depth.claims >= len(dossier["claims"])
    assert ajrakh.depth.stages >= len(dossier["stages"])
    assert ajrakh.depth.pictures == len(dossier["pictures"])
    assert ajrakh.depth.places == located
    assert ajrakh.gi_year == int(dossier["market"]["gi"]["registeredOn"][:4])
    assert ajrakh.hero is not None
    assert ajrakh.hero.page_url in {picture["pageUrl"] for picture in dossier["pictures"]}
    assert ajrakh.display_name == "Kutch Ajrakh" and ajrakh.palette == "indigo"


async def test_the_summary_counts_the_active_crafts_that_are_not_catch_all_rows(
    session: AsyncSession,
) -> None:
    catalogue = CraftCatalogue.model_validate(await load_catalogue(session))
    readers = await session.scalar(
        select(func.count()).select_from(Craft).where(Craft.status == "ACTIVE", Craft.isCatchAll.is_(False))
    )
    assert catalogue.summary.crafts == readers
    assert all(concept.craft_slugs for concept in catalogue.concepts)
    catch_alls = {row.slug for row in catalogue.crafts if row.is_catch_all}
    assert not catch_alls & {slug for concept in catalogue.concepts for slug in concept.craft_slugs}


async def test_a_material_shared_by_curated_crafts_is_a_searchable_concept(session: AsyncSession) -> None:
    imported(await import_curation(session), AJRAKH)
    catalogue = CraftCatalogue.model_validate(await load_catalogue(session))
    indigo = next(concept for concept in catalogue.concepts if concept.key == "indigo")
    assert AJRAKH in indigo.craft_slugs
