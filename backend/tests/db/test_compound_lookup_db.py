from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import Compound, Source
from app.services.claim_seed import seed_id
from app.services.compound_lookup import link_compounds
from app.sources.reference.pubchem import PubChemCompound

from ..science.test_compound_lookup import FakeFinder

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)
ALIZARIN = PubChemCompound(
    6293,
    "Alizarin",
    "C14H8O4",
    "240.21",
    "1,2-dihydroxyanthracene-9,10-dione",
    "RGCKGOZRHPZPFP-UHFFFAOYSA-N",
    None,
)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            yield session
            await session.close()
        finally:
            await transaction.rollback()


async def test_a_seeded_compound_is_linked_to_its_pubchem_record(session: AsyncSession) -> None:
    report = await link_compounds(session, FakeFinder({"Alizarin": [ALIZARIN]}), now=NOW)
    assert report.linked == ["Alizarin"]
    assert "Indigo" in report.not_found and report.failed == []
    alizarin = await session.get(Compound, seed_id("compound", "alizarin"))
    assert (alizarin.pubchemCid, alizarin.formula, alizarin.molecularWeight) == (
        6293,
        "C14H8O4",
        Decimal("240.21"),
    )
    source = await session.get(Source, alizarin.sourceId)
    assert (source.kind, source.url, source.reliability) == (
        "COMPOUND_RECORD",
        "https://pubchem.ncbi.nlm.nih.gov/compound/6293",
        "A",
    )
    again = await link_compounds(session, FakeFinder({"Alizarin": [ALIZARIN]}), now=NOW)
    assert again.linked == []
    sources = (await session.scalars(select(Source).where(Source.url == source.url))).all()
    assert len(sources) == 1
