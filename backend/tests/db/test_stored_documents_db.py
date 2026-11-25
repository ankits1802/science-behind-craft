import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.craft_monograph import DocumentAsk, served_document
from app.core.db import get_engine
from app.models import ArticleSection, Craft, StoredDocumentVersion, User
from app.research.page_layout import LayoutWrite
from app.services import stored_documents
from app.services.app_settings import set_value
from app.services.monograph_document import document_body, document_hash
from app.services.monograph_generated import generated_document
from app.services.open_work_subjects import WorkSubject, subject_by_key
from app.services.page_layouts import write_layout
from app.services.stored_document_rebuilds import (
    DOCUMENT_CODE_SETTING,
    DocumentsReport,
    mark_rebuild_code,
    rebuild_stale_documents,
    rebuilds_here,
)
from app.services.stored_document_stamp import document_stamp
from app.services.stored_document_versions import page_lock_id
from app.services.stored_documents import (
    Rebuilt,
    StoredCopy,
    claim_rebuild,
    read_generated,
    rebuild_document,
    stored_copy,
    stored_row,
    superseded_copy,
)

from .page_documents_seed import (
    ADMIN,
    BARE_SLUG,
    CATEGORY_SLUG,
    CRAFT,
    CRAFT_SLUG,
    CRAFT_TEXT,
    FAMILY_SLUG,
    seed,
)
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 21, 9, 0, tzinfo=UTC)
SECTIONS_VERSION = 3


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        yield opened


async def craft(session: AsyncSession) -> WorkSubject:
    return await subject_by_key(session, "craft", CRAFT_SLUG)


async def laid_out(session: AsyncSession) -> None:
    built = await generated_document(session, "craft", CRAFT_SLUG)
    assert built is not None
    sentence = next(key for key, unit in built.content.units.items() if CRAFT_TEXT[:20] in str(unit.nodes))
    entries = [{"ref": sentence, "chapter": "glance", "order": 1, "role": "PULL_QUOTE"}]
    await write_layout(
        session,
        "craft",
        CRAFT_SLUG,
        LayoutWrite.model_validate({"baseVersion": 0, "entries": entries}),
        actor=await session.get(User, ADMIN),
    )


def stored_document_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == stored_documents.logger.name]


def never_assembled(monkeypatch: pytest.MonkeyPatch) -> None:
    async def refused(session: Any, subject: Any) -> None:
        raise AssertionError(f"{subject.slug} was assembled inside a read that holds a copy")

    monkeypatch.setattr(stored_documents, "generated_document_of", refused)


async def test_the_first_read_builds_and_stores_the_document_and_later_reads_serve_the_copy(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = await craft(session)
    first = await stored_copy(session, subject)
    built = await generated_document(session, "craft", CRAFT_SLUG)
    assert first is not None and built is not None
    assert (first.current, first.version, first.language) == (True, SECTIONS_VERSION, "en")
    assert first.content_hash == document_hash(built)
    assert first.body() == document_body(built)
    assert first.etag == f"v{SECTIONS_VERSION}-{document_hash(built)}"
    row = await stored_row(session, subject)
    assert row is not None and row.wantedAt is None
    assert row.stamp == await document_stamp(session, subject)
    never_assembled(monkeypatch)
    again = await stored_copy(session, subject)
    assert again == first


async def test_a_read_after_the_page_changed_serves_the_last_good_copy_and_queues_one_rebuild(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = await craft(session)
    first = await stored_copy(session, subject)
    assert first is not None
    await laid_out(session)
    never_assembled(monkeypatch)
    stale = await read_generated(session, subject, now=NOW)
    assert stale.copy is not None
    assert (stale.copy.text, stale.copy.current, stale.rebuild) == (first.text, False, True)
    soon = await read_generated(session, subject, now=NOW + timedelta(minutes=5))
    assert soon.copy is not None and (soon.copy.text, soon.rebuild) == (first.text, False)
    later = await read_generated(session, subject, now=NOW + timedelta(minutes=11))
    assert later.rebuild is True


async def test_the_rebuild_stores_the_changed_document_under_the_next_version_and_reads_are_current(
    session: AsyncSession,
) -> None:
    subject = await craft(session)
    first = await stored_copy(session, subject)
    assert first is not None
    await laid_out(session)
    assert await claim_rebuild(session, subject, now=NOW) is True
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.CHANGED
    row = await stored_row(session, subject)
    assert row is not None
    assert (row.version, row.wantedAt, row.builtAt) == (SECTIONS_VERSION + 1, None, NOW)
    after = await stored_copy(session, subject)
    assert after is not None and after.current is True
    assert (after.version, after.body()["version"]) == (SECTIONS_VERSION + 1, SECTIONS_VERSION + 1)
    assert after.body()["content"]["data"]["page-layout"]["version"] == 1
    assert after.etag != first.etag
    assert await rebuild_document(session, subject, now=NOW + timedelta(hours=1)) == Rebuilt.UNCHANGED
    kept = await stored_row(session, subject)
    assert kept is not None and (kept.version, kept.builtAt) == (
        SECTIONS_VERSION + 1,
        NOW + timedelta(hours=1),
    )


async def kept_versions(session: AsyncSession) -> int:
    counted = await session.scalar(
        select(func.count()).where(StoredDocumentVersion.subjectSlug == CRAFT_SLUG)
    )
    return int(counted or 0)


async def test_a_rebuild_keeps_the_version_it_replaces_readable_and_keeps_nothing_it_did_not_replace(
    session: AsyncSession,
) -> None:
    subject = await craft(session)
    first = await stored_copy(session, subject)
    assert first is not None and first.version == SECTIONS_VERSION
    assert await superseded_copy(session, subject, SECTIONS_VERSION) is None
    await laid_out(session)
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.CHANGED
    kept = await superseded_copy(session, subject, SECTIONS_VERSION)
    assert kept is not None
    assert kept == StoredCopy(first.text, SECTIONS_VERSION, first.content_hash, "en", current=False)
    assert kept.etag == first.etag
    assert await superseded_copy(session, subject, SECTIONS_VERSION + 1) is None
    assert await superseded_copy(session, subject, SECTIONS_VERSION, language="hi") is None
    assert await rebuild_document(session, subject, now=NOW + timedelta(hours=1)) == Rebuilt.UNCHANGED
    assert await kept_versions(session) == 1


async def test_a_page_drawn_at_the_version_a_rebuild_replaced_still_reads_it_and_an_unknown_one_reads_none(
    session: AsyncSession,
) -> None:
    subject = await craft(session)
    first = await stored_copy(session, subject)
    assert first is not None
    await laid_out(session)
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.CHANGED
    row = await session.get(Craft, CRAFT)
    assert row is not None
    earlier = await served_document(session, row, DocumentAsk(language="en", version=SECTIONS_VERSION))
    assert earlier is not None
    assert (earlier.text, earlier.version, earlier.etag) == (first.text, SECTIONS_VERSION, first.etag)
    latest = await served_document(session, row, DocumentAsk(language="en"))
    assert latest is not None and latest.version == SECTIONS_VERSION + 1
    assert (
        await served_document(session, row, DocumentAsk(language="en", version=SECTIONS_VERSION + 5)) is None
    )


async def test_a_withdrawn_page_takes_its_superseded_versions_with_it(session: AsyncSession) -> None:
    subject = await craft(session)
    assert await stored_copy(session, subject) is not None
    await laid_out(session)
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.CHANGED
    assert await kept_versions(session) == 1
    await session.execute(
        update(ArticleSection).where(ArticleSection.craftId == CRAFT).values(status="SUPERSEDED")
    )
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.REMOVED
    assert await superseded_copy(session, subject, SECTIONS_VERSION) is None
    assert await kept_versions(session) == 0


async def test_a_read_that_races_a_finished_rebuild_claims_no_second_one(session: AsyncSession) -> None:
    subject = await craft(session)
    assert await stored_copy(session, subject) is not None
    await laid_out(session)
    assert await claim_rebuild(session, subject, now=NOW) is True
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.CHANGED
    assert await claim_rebuild(session, subject, now=NOW + timedelta(seconds=1)) is False


async def test_inputs_that_move_while_a_document_is_built_raise_no_alarm_and_leave_it_to_be_built_again(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    subject = await craft(session)
    assert await stored_copy(session, subject) is not None
    built = stored_documents.generated_document_of

    async def moved_while_built(opened: AsyncSession, asked: WorkSubject) -> Any:
        await laid_out(opened)
        return await built(opened, asked)

    monkeypatch.setattr(stored_documents, "generated_document_of", moved_while_built)
    with caplog.at_level(logging.INFO, logger="app.services.stored_documents"):
        assert await rebuild_document(session, subject, now=NOW) == Rebuilt.CHANGED
    monkeypatch.setattr(stored_documents, "generated_document_of", built)
    reported = stored_document_records(caplog)
    assert [record.levelno for record in reported] == [logging.INFO]
    assert "moved while it was built" in reported[0].getMessage()
    later = await read_generated(session, subject, now=NOW + timedelta(seconds=1))
    assert later.copy is not None and (later.copy.current, later.rebuild) == (False, True)


async def test_a_document_that_changes_while_its_inputs_stand_still_is_reported(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    subject = await craft(session)
    assert await stored_copy(session, subject) is not None
    built = stored_documents.generated_document_of

    async def retitled(opened: AsyncSession, asked: WorkSubject) -> Any:
        document = await built(opened, asked)
        return None if document is None else document.model_copy(update={"title": "A title no input gave"})

    monkeypatch.setattr(stored_documents, "generated_document_of", retitled)
    with caplog.at_level(logging.INFO, logger="app.services.stored_documents"):
        assert await rebuild_document(session, subject, now=NOW) == Rebuilt.CHANGED
    reported = stored_document_records(caplog)
    assert [record.levelno for record in reported] == [logging.ERROR]
    assert "an input the stamp misses moved" in reported[0].getMessage()


async def test_a_page_whose_sections_are_withdrawn_loses_its_stored_document(session: AsyncSession) -> None:
    subject = await craft(session)
    assert await stored_copy(session, subject) is not None
    await session.execute(
        update(ArticleSection).where(ArticleSection.craftId == CRAFT).values(status="SUPERSEDED")
    )
    assert await stored_copy(session, subject) is None
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.REMOVED
    assert await stored_row(session, subject) is None
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.ABSENT


async def test_the_release_rebuilds_every_stale_document_and_a_second_sweep_finds_them_current(
    session: AsyncSession,
) -> None:
    seeded = {f"craft:{CRAFT_SLUG}", f"family:{FAMILY_SLUG}", f"category:{CATEGORY_SLUG}"}
    report = DocumentsReport()
    await rebuild_stale_documents(session, report=report, limit=10_000)
    assert seeded <= set(report.rebuilt)
    assert f"craft:{BARE_SLUG}" not in report.rebuilt
    assert report.failed == []
    again = DocumentsReport()
    await rebuild_stale_documents(session, report=again, limit=10_000)
    assert not seeded & set(again.rebuilt)
    assert await rebuilds_here(session) is True


async def test_only_the_release_that_last_rebuilt_documents_rebuilds_after_a_read(
    session: AsyncSession,
) -> None:
    await set_value(session, DOCUMENT_CODE_SETTING, "a release that has gone")
    assert await rebuilds_here(session) is False
    await mark_rebuild_code(session)
    assert await rebuilds_here(session) is True


async def page_free_elsewhere(kind: str, slug: str) -> bool:
    async with get_engine().connect() as other:
        taken = await other.scalar(select(func.pg_try_advisory_xact_lock(page_lock_id(kind, slug))))
        await other.rollback()
    return bool(taken)


async def test_a_rebuild_holds_its_page_before_it_reads_the_version_so_a_second_waits_and_others_do_not(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = await craft(session)
    built = stored_documents.generated_document_of
    seen: list[tuple[bool, bool, bool]] = []

    async def watched(opened: AsyncSession, asked: WorkSubject) -> Any:
        held = await page_free_elsewhere("craft", CRAFT_SLUG), await page_free_elsewhere("family", CRAFT_SLUG)
        seen.append((*held, await page_free_elsewhere("category", CATEGORY_SLUG)))
        return await built(opened, asked)

    monkeypatch.setattr(stored_documents, "generated_document_of", watched)
    assert await page_free_elsewhere("craft", CRAFT_SLUG) is True
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.BUILT
    assert seen == [(False, False, True)]
