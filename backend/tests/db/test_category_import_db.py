import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import (
    Claim,
    ClaimSource,
    Concept,
    CraftCategory,
    CuratedCategory,
    CuratedCategoryClaim,
    KnowledgePiece,
    MediaRefClaim,
    ReviewEvent,
    TermConcept,
)
from app.research.category_page import CategoryList, CategoryPage
from app.services.category_import import CategoryImportReport, category_curated_claims, import_categories
from app.services.category_page import category_list, category_page
from app.services.category_records import category_list_records, category_page_records
from app.services.curation_keys import curated_id

from ..contracts.golden import golden_json
from ..curation.category_support import (
    LEATHER,
    LIST_GOLDEN,
    PAGE_GOLDEN,
    copy_fixture,
    dropped_version,
    leather_plain,
)

pytestmark = pytest.mark.db

DROPPED = "C170"
PICTURE_LINKS = 4


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


async def count(session: AsyncSession, *conditions: Any, model: Any = Claim) -> int:
    return (await session.execute(select(func.count()).select_from(model).where(*conditions))).scalar_one()


async def leather_id(session: AsyncSession) -> uuid.UUID:
    found = await session.scalar(select(CraftCategory.id).where(CraftCategory.slug == LEATHER))
    assert found is not None
    return found


def imported(report: CategoryImportReport) -> Any:
    assert report.refused == [], [outcome.problems for outcome in report.refused]
    return next(outcome for outcome in report.outcomes if outcome.category_slug == LEATHER)


async def import_fixture(session: AsyncSession, directory: Path) -> Any:
    copy_fixture(directory)
    return imported(await import_categories(session, directory=directory))


async def test_the_fixture_imports_claims_sources_pictures_glossary_and_overview(
    session: AsyncSession, tmp_path: Path
) -> None:
    outcome = await import_fixture(session, tmp_path)
    assert (outcome.status, outcome.version) == ("IMPORTED", 1)
    plain = leather_plain()
    marked = category_curated_claims(await leather_id(session))
    assert await count(session, Claim.id.in_(marked)) == len(plain["claims"])
    assert await count(session, Claim.id.in_(marked), Claim.status != "APPROVED") == 0
    quotes = sum(len(claim["quotes"]) for claim in plain["claims"])
    assert await count(session, ClaimSource.claimId.in_(marked), model=ClaimSource) == quotes
    subjects = select(Claim.subjectId).where(Claim.id.in_(marked))
    assert await count(session, Concept.id.in_(subjects), Concept.craftId.is_not(None), model=Concept) == 0
    assert await count(session, MediaRefClaim.claimId.in_(marked), model=MediaRefClaim) == PICTURE_LINKS
    terms = select(Concept.id).where(Concept.originRef.like(f"curation:{LEATHER}:W%"))
    assert await count(session, TermConcept.conceptId.in_(terms), model=TermConcept) == len(plain["glossary"])
    stored = (
        await session.execute(
            select(CuratedCategory).where(CuratedCategory.categoryId == await leather_id(session))
        )
    ).scalar_one()
    assert (stored.version, stored.coverage) == (1, "THIN")
    overview = stored.page["overview"]
    pieces = [uuid.UUID(overview["ledePieceId"]), *(uuid.UUID(s["pieceId"]) for s in overview["sections"])]
    assert len(pieces) == 2
    assert (
        await count(
            session, KnowledgePiece.id.in_(pieces), KnowledgePiece.craftId.is_(None), model=KnowledgePiece
        )
        == 2
    )


async def test_the_served_page_and_list_entry_match_the_goldens(
    session: AsyncSession, tmp_path: Path
) -> None:
    await import_fixture(session, tmp_path)
    records = await category_page_records(session, LEATHER)
    assert records is not None
    assert category_page(records) == CategoryPage.model_validate(golden_json(PAGE_GOLDEN))
    listing = category_list(await category_list_records(session))
    golden = CategoryList.model_validate(golden_json(LIST_GOLDEN))
    served = next(entry for entry in listing.categories if entry.slug == LEATHER)
    assert served == next(entry for entry in golden.categories if entry.slug == LEATHER)
    assert listing.sources == golden.sources


async def test_a_second_import_changes_nothing(session: AsyncSession, tmp_path: Path) -> None:
    await import_fixture(session, tmp_path)
    events = await count(session, model=ReviewEvent)
    rows = await _curated_rows(session)
    again = await import_categories(session, directory=tmp_path)
    assert [outcome.changed for outcome in again.outcomes] == [{}]
    assert await count(session, model=ReviewEvent) == events
    assert await _curated_rows(session) == rows


async def _curated_rows(session: AsyncSession) -> list[Any]:
    statement = (
        select(Claim.id, Claim.text, Claim.status, Claim.evidenceLevel, Claim.version, Claim.sourcesDiffer)
        .join(CuratedCategoryClaim, CuratedCategoryClaim.claimId == Claim.id)
        .order_by(Claim.id)
    )
    return list((await session.execute(statement)).tuples().all())


async def test_a_new_version_supersedes_a_dropped_claim_and_keeps_its_citations(
    session: AsyncSession, tmp_path: Path
) -> None:
    await import_fixture(session, tmp_path / "first")
    dropped = curated_id(LEATHER, DROPPED)
    citations = await count(session, ClaimSource.claimId == dropped, model=ClaimSource)
    assert citations >= 1
    dropped_version(tmp_path / "second", DROPPED)
    outcome = imported(await import_categories(session, directory=tmp_path / "second"))
    assert outcome.version == 2
    claim = (await session.execute(select(Claim).where(Claim.id == dropped))).scalar_one()
    assert claim.status == "SUPERSEDED"
    assert await count(session, ClaimSource.claimId == dropped, model=ClaimSource) == citations
    assert await count(session, CuratedCategoryClaim.claimId == dropped, model=CuratedCategoryClaim) == 1
    assert await count(session, MediaRefClaim.claimId == dropped, model=MediaRefClaim) == 0
    assert (
        await count(
            session, ReviewEvent.claimId == dropped, ReviewEvent.toStatus == "SUPERSEDED", model=ReviewEvent
        )
        == 1
    )
    version = await session.scalar(
        select(CuratedCategory.version).where(CuratedCategory.categoryId == await leather_id(session))
    )
    assert version == 2
    records = await category_page_records(session, LEATHER)
    assert records is not None
    assert dropped not in {claim.id for claim in category_page(records).claims}


async def test_a_category_dossier_without_its_check_file_writes_nothing(
    session: AsyncSession, tmp_path: Path
) -> None:
    path = copy_fixture(tmp_path)
    path.with_name(f"{LEATHER}.check.json").unlink()
    before = await count(session, model=CuratedCategoryClaim)
    report = await import_categories(session, directory=tmp_path)
    assert [outcome.status for outcome in report.outcomes] == ["REFUSED"]
    assert await count(session, model=CuratedCategoryClaim) == before
