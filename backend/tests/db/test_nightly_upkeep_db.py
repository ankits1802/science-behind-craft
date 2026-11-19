import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Claim, ClaimSource, Craft, CraftPageSnapshot, Source, SourceUpkeep
from app.services.static_pages import static_pages
from app.services.upkeep_archive import archive_sources, sources_at_risk
from app.services.upkeep_quotes import recheck_quotes, sources_due

from ..upkeep.fakes import ScriptedArchiver, ScriptedFetcher, fetched_page, gone
from .accounts import bearer, create_user, login, unique_email
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 20, 0, 30, tzinfo=UTC)
LONG_AGO = NOW - timedelta(days=45)
LATELY = NOW - timedelta(days=3)
SITE = "https://upkeep-test.example.org"
CRAFT = uuid.UUID("5e1f0000-0000-4000-8000-000000000001")
CONCEPT_SUBJECT = uuid.UUID("5e1f0000-0000-4000-8000-000000000002")
TEXT = "Harde, the fruit of Terminalia chebula, gives the cloth its first yellow."


def source_id(n: int) -> uuid.UUID:
    return uuid.UUID(f"5e1f0000-0000-4000-8000-1000000000{n:02d}")


def claim_source_id(n: int) -> uuid.UUID:
    return uuid.UUID(f"5e1f0000-0000-4000-8000-2000000000{n:02d}")


async def cited(session: AsyncSession, n: int, quotes: list[str | None], **source: object) -> None:
    session.add(Source(id=source_id(n), kind="WEB_PAGE", title=f"Upkeep source {n}", **source))
    claim = uuid.uuid4()
    session.add(
        Claim(
            id=claim,
            subjectType="CONCEPT",
            subjectId=CONCEPT_SUBJECT,
            predicate="states",
            text=TEXT,
            evidenceLevel="PROVISIONAL",
            origin="IMPORT",
        )
    )
    await session.flush()
    for k, quote in enumerate(quotes):
        session.add(
            ClaimSource(id=claim_source_id(n * 10 + k), claimId=claim, sourceId=source_id(n), quote=quote)
        )
    await session.flush()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await cited(
            opened, 1, ["the fruit of Terminalia chebula", "boiled in alum for an hour"], url=f"{SITE}/harde"
        )
        await cited(opened, 2, ["anything"], url=f"{SITE}/gone")
        await cited(opened, 3, ["anything"], url=f"{SITE}/recent")
        await cited(opened, 4, ["anything"], url="http://upkeep-test.example.org/plain")
        await cited(opened, 5, [None], url=f"{SITE}/old")
        opened.add(SourceUpkeep(sourceId=source_id(3), checkedAt=LATELY, outcome="FETCHED"))
        opened.add(SourceUpkeep(sourceId=source_id(5), checkedAt=LONG_AGO, outcome="FETCHED"))
        await opened.flush()
        yield opened


def mine(ids: list[uuid.UUID]) -> list[int]:
    numbers = {source_id(n): n for n in range(1, 6)}
    return [numbers[found] for found in ids if found in numbers]


async def test_unchecked_sources_come_first_then_the_longest_unchecked(session: AsyncSession) -> None:
    due = await sources_due(session, now=NOW, limit=100_000)
    assert mine([entry.source_id for entry in due]) == [1, 2, 5]


async def test_a_recheck_records_each_quote_and_the_source_s_fetch(session: AsyncSession) -> None:
    fetcher = ScriptedFetcher(
        {f"{SITE}/harde": fetched_page(f"{SITE}/harde", TEXT), f"{SITE}/gone": gone(SITE)}
    )
    await recheck_quotes(session, fetcher, now=NOW, limit=100_000)
    checks = dict(
        (
            await session.execute(
                select(ClaimSource.id, ClaimSource.quoteCheck).where(ClaimSource.sourceId == source_id(1))
            )
        ).all()
    )
    assert checks == {claim_source_id(10): "PASS", claim_source_id(11): "FAIL"}
    kept = {row.sourceId: row for row in (await session.scalars(select(SourceUpkeep))).all()}
    assert (kept[source_id(1)].outcome, kept[source_id(1)].failures, kept[source_id(1)].checkedAt) == (
        "FETCHED",
        0,
        NOW,
    )
    assert (kept[source_id(2)].outcome, kept[source_id(2)].failures, kept[source_id(2)].problem) == (
        "FAILED",
        1,
        "not_found 404",
    )
    assert kept[source_id(3)].checkedAt == LATELY


async def test_a_link_that_stays_dead_counts_its_failures(session: AsyncSession) -> None:
    fetcher = ScriptedFetcher({f"{SITE}/gone": gone(SITE)})
    await recheck_quotes(session, fetcher, now=NOW, limit=100_000)
    await recheck_quotes(session, fetcher, now=NOW + timedelta(days=31), limit=100_000)
    kept = await session.get(SourceUpkeep, source_id(2), populate_existing=True)
    assert kept is not None and (kept.outcome, kept.failures) == ("FAILED", 2)


async def test_only_open_live_unarchived_sources_without_a_doi_are_archived(session: AsyncSession) -> None:
    await cited(session, 6, ["x"], url=f"{SITE}/restricted", sensitivity="RESTRICTED")
    await cited(session, 7, ["x"], url=f"{SITE}/doi", doi="10.5555/upkeep-test")
    await cited(
        session,
        8,
        ["x"],
        url=f"{SITE}/kept",
        externalIds={"archivedUrl": "https://web.archive.org/web/2025/x"},
    )
    for n in (6, 7, 8):
        session.add(SourceUpkeep(sourceId=source_id(n), checkedAt=LONG_AGO, outcome="FETCHED"))
    await session.flush()
    at_risk = await sources_at_risk(session, now=NOW, limit=100_000)
    assert mine([entry.source_id for entry in at_risk]) == [3, 5]
    archiver = ScriptedArchiver()
    report = await archive_sources(session, archiver, now=NOW, limit=100_000)
    assert f"{SITE}/old" in archiver.saved
    kept = await session.get(SourceUpkeep, source_id(5), populate_existing=True)
    assert kept is not None
    assert kept.archiveUrl == f"https://web.archive.org/web/20261120003000/{SITE}/old"
    assert str(source_id(5)) in report.archived
    assert mine([entry.source_id for entry in await sources_at_risk(session, now=NOW, limit=100_000)]) == []


async def test_the_static_page_list_holds_crafts_with_an_open_snapshot(session: AsyncSession) -> None:
    session.add(Craft(id=CRAFT, name="Upkeep Test Craft", slug="Upkeep-Test-Craft"))
    await session.flush()
    session.add(
        CraftPageSnapshot(
            craftId=CRAFT, variant="OPEN", stamp="s", schemaVersion=1, body={}, etag="e", builtAt=NOW
        )
    )
    await session.flush()
    listed = await static_pages(session)
    assert "Upkeep-Test-Craft" in listed.crafts
    assert listed.as_dict()["schemaVersion"] == 1


async def signed_in(client: httpx.AsyncClient, role: str) -> str:
    email = unique_email(f"upkeep-{role.lower().replace('_', '-')}")
    secret = await create_user(email, role, with_two_factor=True)
    return await login(client, email, secret)


async def test_only_an_admin_reaches_the_build_trigger(client: httpx.AsyncClient) -> None:
    professor = await signed_in(client, "PROFESSOR")
    admin = await signed_in(client, "ADMIN")
    assert (await client.post("/api/site/build", headers=bearer(professor))).status_code == 403
    assert (await client.get("/api/site/build", headers=bearer(professor))).status_code == 403
    state = await client.get("/api/site/build", headers=bearer(admin))
    assert state.status_code == 200
    assert state.json()["configured"] is False
    unset = await client.post("/api/site/build", headers=bearer(admin))
    assert unset.status_code == 503
