import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import EnvDataset
from app.research.blocks import named_in
from app.research.datasets import BOUNDARY_DATASET_CODE
from app.research.image_relevance import ChosenImage, Illustration
from app.research.images import ImageCandidate
from app.services.builder_evidence import fact_sentence
from app.services.media_ref_store import SqlMediaStore, stored_pictures
from app.services.zoom_story import ZOOM_DISTRICT_CLAIMS_MAX, zoom_ground

from ..geo.golden_region import golden_datasets
from .test_media_refs_db import RETRIEVED, VAM_IMAGE, VAM_PAGE
from .test_place_db import locate_in_kachchh

pytestmark = pytest.mark.db

RESIST_PASTE = uuid.UUID("f363ce3a-c4a6-5b24-87e7-2634e18175cf")
COMMONS_PAGE = "https://commons.wikimedia.org/wiki/File:Ajrak_Printing_Materials_1.jpg"
COMMONS_IMAGE = (
    "https://thumb.wikimedia.org/wikipedia/commons/thumb/4/4e/Ajrak_Printing_Materials_1.jpg/"
    "960px-Ajrak_Printing_Materials_1.jpg"
)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            await session.execute(delete(EnvDataset))
            boundary = golden_datasets()[BOUNDARY_DATASET_CODE]
            session.add(
                EnvDataset(
                    id=uuid.uuid4(),
                    code=boundary.code,
                    title=boundary.title,
                    publisher=boundary.publisher,
                    edition=boundary.edition,
                    period=boundary.period,
                    nativeResolution=boundary.native_resolution,
                    licence=boundary.licence,
                    licenceUrl=boundary.licence_url,
                    attribution=boundary.attribution,
                    citation=boundary.citation,
                    url=boundary.url,
                )
            )
            await session.flush()
            yield session
            await session.close()
        finally:
            await transaction.rollback()


def keeper(session: AsyncSession) -> SqlMediaStore:
    def sessions() -> AsyncSession:
        return AsyncSession(bind=session.bind, expire_on_commit=False, autoflush=False)

    return SqlMediaStore(sessions)


def picture(page: str, image: str, *, licence: str | None, author: str | None) -> ChosenImage:
    candidate = ImageCandidate(
        provider="wikimedia_commons" if licence else "searxng",
        page_url=page,
        image_url=image,
        original_url=image,
        title="Ajrak Printing Materials 1",
        description="Sticky gums used during indigo printing.",
        author=author,
        site="Wikimedia Commons" if licence else "collections.vam.ac.uk",
        licence=licence,
        retrieved_at=RETRIEVED,
    )
    return ChosenImage(candidate, Illustration(claim_ids=(RESIST_PASTE,), shared=2))


async def test_only_open_pictures_kept_for_a_claim_are_read_back(session: AsyncSession) -> None:
    licensed = picture(COMMONS_PAGE, COMMONS_IMAGE, licence="CC BY-SA 4.0", author="SMarndi")
    card = picture(VAM_PAGE, VAM_IMAGE, licence=None, author=None)
    kept = await keeper(session).keep([licensed, card])
    found = await stored_pictures(session, [uuid.uuid4(), RESIST_PASTE])
    assert [(p.media.id, p.claim_id, p.relevance) for p in found] == [(kept[0].id, RESIST_PASTE, "TEXT")]
    assert (kept[0].display, kept[1].display) == ("INLINE", "LINK_CARD")
    assert await stored_pictures(session, []) == []


async def test_the_zoom_ground_is_the_craft_s_mapped_district_its_naming_claims_and_pictures(
    session: AsyncSession,
) -> None:
    await locate_in_kachchh(session)
    await session.flush()
    await keeper(session).keep([picture(COMMONS_PAGE, COMMONS_IMAGE, licence="CC0", author="SMarndi")])
    ground = await zoom_ground(session, "Kutch-Ajrakh", mode="HYBRID", offered=[RESIST_PASTE])
    assert ground is not None
    assert [(d.district_lgd, d.name, d.state_name) for d in ground.districts] == [(449, "Kachchh", "Gujarat")]
    assert ground.boundary is not None and ground.boundary.code == BOUNDARY_DATASET_CODE
    assert 1 <= len(ground.claims) <= ZOOM_DISTRICT_CLAIMS_MAX
    assert all(named_in("Kachchh", fact_sentence(claim, "x")) for claim in ground.claims)
    cited = {citation.source_id for claim in ground.claims for citation in claim.citations}
    assert set(ground.sources) == cited
    assert [picture.claim_id for picture in ground.pictures] == [RESIST_PASTE]


async def test_without_the_boundary_row_the_zoom_reads_no_district_claims(session: AsyncSession) -> None:
    await locate_in_kachchh(session)
    await session.execute(delete(EnvDataset))
    ground = await zoom_ground(session, "Kutch-Ajrakh", mode="HYBRID", offered=[])
    assert ground is not None
    assert (ground.boundary, ground.claims, ground.pictures) == (None, (), ())
    assert await zoom_ground(session, "not-a-craft", mode="HYBRID", offered=[]) is None
