import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.research.craft_catalogue import CraftCatalogue
from app.services.craft_catalogue import load_catalogue
from app.services.curation_import import import_curation
from app.services.curation_keys import curated_id
from app.services.public_summary import (
    SPECIMEN_CLAIM_KEY,
    SPECIMEN_CRAFT_SLUG,
    public_summary,
    summary_records,
)

from ..curation.import_support import AJRAKH
from .test_curation_import_db import imported, session

pytestmark = pytest.mark.db

__all__ = ["session"]


async def test_the_summary_counts_are_the_catalogue_s_and_ajrakh_is_featured_and_cited(
    session: AsyncSession,
) -> None:
    imported(await import_curation(session), AJRAKH)
    summary = public_summary(await summary_records(session))
    catalogue = CraftCatalogue.model_validate(await load_catalogue(session))
    assert summary.counts == catalogue.summary
    ajrakh = next(entry for entry in summary.featured if entry.craft.slug == AJRAKH)
    assert ajrakh.hero is not None
    assert all(citation.quote for citation in ajrakh.lede.citations)
    assert summary.specimen is not None and summary.specimen.craft.slug == SPECIMEN_CRAFT_SLUG
    claim = str(curated_id(SPECIMEN_CRAFT_SLUG, SPECIMEN_CLAIM_KEY))
    assert claim in {citation.claim_id for citation in summary.specimen.sentence.citations}


async def test_the_placed_points_carry_only_crafts_the_catalogue_counts(session: AsyncSession) -> None:
    imported(await import_curation(session), AJRAKH)
    summary = public_summary(await summary_records(session))
    catalogue = CraftCatalogue.model_validate(await load_catalogue(session))
    counted = {craft.slug for craft in catalogue.crafts if not craft.is_catch_all}
    assert summary.points
    assert all(craft.slug in counted for point in summary.points for craft in point.curated)
    assert AJRAKH in {craft.slug for point in summary.points for craft in point.curated}
