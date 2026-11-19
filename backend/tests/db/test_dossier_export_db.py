import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.curation.files import CURATION_DIR, check_path
from app.models import Claim, ReviewEvent
from app.services.category_import import import_categories
from app.services.curation_import import import_curation
from app.services.curation_keys import curated_id
from app.services.dossier_export import CURRENT, LAYOUT, SAME, export_dossier, export_dossiers

from ..curation.import_support import AJRAKH

pytestmark = pytest.mark.db

RETRACTED = "RETRACTED"
CATEGORY_PREFIX = "categories/"


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


async def _events(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(ReviewEvent))).scalar_one()


async def _import_all(session: AsyncSession, directory: Path = CURATION_DIR) -> dict[str, Any]:
    crafts = await import_curation(session, directory=directory)
    categories = await import_categories(session, directory=directory)
    assert crafts.refused == [] and categories.refused == []
    changed = {outcome.file: outcome.changed for outcome in crafts.dossiers if outcome.status == "IMPORTED"}
    return changed | {outcome.file: outcome.changed for outcome in categories.outcomes}


async def test_the_imported_kutch_ajrakh_dossier_exports_as_its_file_in_git(session: AsyncSession) -> None:
    await _import_all(session)
    found = await export_dossier(session, AJRAKH)
    assert found.text == (CURATION_DIR / f"{AJRAKH}.json").read_text(encoding="utf-8")
    assert (found.status, found.check, found.changes, found.reviewed) == (SAME, CURRENT, (), ())


async def test_exporting_then_importing_changes_nothing(session: AsyncSession, tmp_path: Path) -> None:
    first = await _import_all(session)
    run = await export_dossiers(session, [])
    assert run.refused == ()
    assert {export.file for export in run.exports} == set(first)
    for export in run.exports:
        target = tmp_path / export.file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(export.text, encoding="utf-8", newline="\n")
        shutil.copy(check_path(CURATION_DIR / export.file, export.slug), check_path(target, export.slug))
    events = await _events(session)
    again = await _import_all(session, tmp_path)
    for export in run.exports:
        page = "curatedCategory" if export.file.startswith(CATEGORY_PREFIX) else "curatedCraft"
        expected = {page: 1} if export.status == LAYOUT else {}
        assert export.status in (SAME, LAYOUT), (export.file, export.changes)
        assert again[export.file] == expected, export.file
    assert await _events(session) == events


async def test_a_claim_a_review_retracted_is_reported_and_kept(session: AsyncSession) -> None:
    await _import_all(session)
    claim_id = curated_id(AJRAKH, "C001")
    await session.execute(update(Claim).where(Claim.id == claim_id).values(status=RETRACTED))
    found = await export_dossier(session, AJRAKH)
    assert found.reviewed == (f"C001: {RETRACTED}",)
    assert found.status == SAME
