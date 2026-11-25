import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Claim,
    ClaimSource,
    Concept,
    Craft,
    CraftCategory,
    CraftSubCategory,
    MediaRef,
    MediaRefClaim,
    Source,
)
from app.services.craft_page_records import craft_page_records
from app.services.media_ref_store import media_ref_id, media_url_key

from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

TEXTILES = "Textiles based Craft Category"
BLOCK_PRINTING = "Hand Block Printing"
PICTURES = "https://pictures.example.org"
RETRIEVED = datetime(2026, 11, 25, 6, 0, tzinfo=UTC)
DHAMADKA = "stretch of art, dhamadka kutch"
STAMPED = "Akola printers stamp a dabu resist of clay and gum on the cloth before it is dyed."


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        yield opened


async def akola(session: AsyncSession) -> tuple[Craft, uuid.UUID]:
    kind = await session.scalar(
        select(CraftSubCategory.id)
        .join(CraftCategory, CraftCategory.id == CraftSubCategory.categoryId)
        .where(CraftCategory.name == TEXTILES, CraftSubCategory.name == BLOCK_PRINTING)
    )
    assert kind is not None
    token = uuid.uuid4().hex[:8]
    craft = Craft(
        id=uuid.uuid4(),
        slug=f"Akola-Pictures-{token}",
        name="Block Printing Of Akola",
        subCategoryId=kind,
        stateOfPractice=["Rajasthan"],
    )
    session.add(craft)
    await session.flush()
    concept = Concept(craftId=craft.id, type="PROCESS_STAGE", name="Dabu resist")
    source = Source(kind="WEB_PAGE", title="Dabu at Akola", url=f"https://akola-{token}.example.org/dabu")
    session.add_all([concept, source])
    await session.flush()
    claim = Claim(
        subjectType="CONCEPT",
        subjectId=concept.id,
        predicate="states",
        text=STAMPED,
        evidenceLevel="PROVISIONAL",
        origin="IMPORT",
        field="PROCESS",
    )
    session.add(claim)
    await session.flush()
    session.add(
        ClaimSource(claimId=claim.id, sourceId=source.id, quote=STAMPED, locator="p. 1", quoteCheck="PASS")
    )
    await session.flush()
    return craft, claim.id


async def linked(session: AsyncSession, claim_id: uuid.UUID, provider: str, title: str) -> uuid.UUID:
    page_url = f"{PICTURES}/{provider}/{uuid.uuid4().hex[:8]}"
    image_url = f"{page_url}.jpg"
    key = media_url_key(provider, page_url, image_url)
    row = MediaRef(
        id=media_ref_id(key),
        urlKey=key,
        display="INLINE",
        provider=provider,
        pageUrl=page_url,
        imageUrl=image_url,
        title=title,
        alt="art, dhamadka, dyeing, kutch",
        author="A",
        site="pictures.example.org",
        licence="CC BY 2.0",
        retrievedAt=RETRIEVED,
    )
    session.add(row)
    await session.flush()
    session.add(MediaRefClaim(mediaRefId=row.id, claimId=claim_id, relevance="TEXT"))
    await session.flush()
    return row.id


async def test_an_uncurated_page_serves_its_world_s_stored_pictures_and_a_searched_one_never_leads(
    session: AsyncSession,
) -> None:
    craft, claim_id = await akola(session)
    elsewhere = await linked(session, claim_id, "openverse", DHAMADKA)
    named = await linked(session, claim_id, "openverse", "Dabu printing at Akola")
    picked = await linked(session, claim_id, "curation", DHAMADKA)
    records = await craft_page_records(session, craft)
    assert records.curated is None and claim_id in {view.id for view in records.views}
    served = {picture.media.id: picture.may_lead for picture in records.pictures}
    assert served == {named: False, picked: True}
    assert elsewhere not in served
