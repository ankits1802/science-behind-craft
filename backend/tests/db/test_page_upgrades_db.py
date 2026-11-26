import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_engine
from app.models import Craft, LayoutProposal, PageLayout, PageUpgrade
from app.research.monograph_document import MonographDocument
from app.research.open_work import OpenTask, Viewer, WorkFilters, parse_task_key
from app.research.page_upgrades import UPGRADE_CUTOFF
from app.services.compose_components import ComposeDeps
from app.services.compose_held import CraftHeld
from app.services.monograph_document import store_document
from app.services.open_work import list_open_work, open_task
from app.services.page_upgrades import built_before_round, raise_page_upgrades, upgrades_due

pytestmark = pytest.mark.db

SITE = "https://kalavigyan.example"
NOW = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
BEFORE = UPGRADE_CUTOFF - timedelta(days=1)
AFTER = UPGRADE_CUTOFF + timedelta(hours=1)
OLD = "Upgrade-Test-Old"
SWAPPED = "Upgrade-Test-Swapped"
NEW = "Upgrade-Test-New"
SYSTEM = "Upgrade-Test-System"
WAITING = "Upgrade-Test-Waiting"
REBUILT = "Upgrade-Test-Rebuilt"
BAR = "Kutch-Ajrakh"
LINE = (
    "history: 3 cited paragraphs run on with no figure, stated by c61, c62, c63; Kutch Ajrakh draws a figure "
    "in every chapter of cited prose, so a figure could carry what they state, among them a coded_figure "
    "written over the chapter's cited data (decision 0231)"
)


async def nothing_held(session: AsyncSession, slug: str) -> CraftHeld | None:
    return None


QUIET = ComposeDeps(held=nothing_held)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            sessions = async_sessionmaker(
                bind=connection,
                expire_on_commit=False,
                autoflush=False,
                join_transaction_mode="create_savepoint",
            )
            async with sessions() as opened:
                yield opened
        finally:
            await transaction.rollback()


def document(slug: str) -> MonographDocument:
    units = {
        f"u-history-{letter}": {
            "chapter": "history",
            "tag": "p",
            "field": "HISTORY",
            "nodes": [f"Printers kept block {letter} in the town."],
            "claimIds": [claim],
        }
        for letter, claim in (("a", "c61"), ("b", "c62"), ("c", "c63"))
    }
    content = {
        "craftSlug": slug,
        "sources": {},
        "citations": {},
        "citationClaims": {},
        "data": {},
        "units": units,
        "components": [],
        "layout": [{"chapter": "history", "kind": "unit", "ref": key} for key in units],
    }
    body = {"subjectKind": "craft", "subjectSlug": slug, "title": slug, "version": 1, "content": content}
    return MonographDocument.model_validate({**body, "pageUrl": f"{SITE}/crafts/{slug}"})


async def craft(session: AsyncSession, slug: str) -> Craft:
    found = await session.scalar(select(Craft).where(Craft.slug == slug))
    if found is not None:
        return found
    made = Craft(
        id=uuid.uuid4(),
        name=slug.replace("-", " "),
        slug=slug,
        stateOfOrigin=["Gujarat"],
        stateOfPractice=["Gujarat"],
    )
    session.add(made)
    await session.flush()
    return made


def proposal(owner: Craft, status: str, at: datetime, version: int | None = None) -> LayoutProposal:
    return LayoutProposal(
        subjectKind="craft",
        craftId=owner.id,
        baseVersion=0 if version is None else version - 1,
        entries=[],
        origin="AGENT",
        status=status,
        reviewedAt=None if status == "PENDING" else at,
        layoutVersion=version,
        createdAt=at,
    )


async def laid(session: AsyncSession, owner: Craft, at: datetime, *, approved: bool) -> int:
    latest = await session.scalar(select(func.max(PageLayout.version)).where(PageLayout.craftId == owner.id))
    version = int(latest or 0) + 1
    session.add(PageLayout(craftId=owner.id, version=version, entries=[], createdAt=at))
    if approved:
        session.add(proposal(owner, "APPROVED", at, version))
    await session.flush()
    return version


async def test_a_page_built_before_the_round_is_raised_once_its_live_page_is_stored(
    session: AsyncSession,
) -> None:
    old = await craft(session, OLD)
    version = await laid(session, old, BEFORE, approved=True)
    early = await raise_page_upgrades(session, compose=QUIET)
    assert f"craft:{OLD}" in early.no_document and f"craft:{OLD}" in await upgrades_due(session)
    await store_document(session, document(OLD))
    first = await raise_page_upgrades(session, compose=QUIET)
    assert f"craft:{OLD}" in first.raised
    row = await session.scalar(select(PageUpgrade).where(PageUpgrade.subjectSlug == OLD))
    assert row is not None and (row.subjectKind, row.layoutVersion, row.lines) == ("craft", version, [LINE])
    second = await raise_page_upgrades(session, compose=QUIET)
    assert f"craft:{OLD}" not in second.raised and second.already_raised >= 1
    held = select(func.count()).select_from(PageUpgrade).where(PageUpgrade.subjectSlug == OLD)
    assert await session.scalar(held) == 1
    assert f"craft:{OLD}" not in await upgrades_due(session)


async def test_only_a_contributor_s_page_whose_last_approved_layout_precedes_the_round_is_built_before_it(
    session: AsyncSession,
) -> None:
    old = await craft(session, OLD)
    await laid(session, old, BEFORE, approved=True)
    swapped = await craft(session, SWAPPED)
    await laid(session, swapped, BEFORE, approved=True)
    await laid(session, swapped, AFTER, approved=False)
    await laid(session, await craft(session, NEW), AFTER, approved=True)
    await laid(session, await craft(session, SYSTEM), BEFORE, approved=False)
    waiting = await craft(session, WAITING)
    await laid(session, waiting, BEFORE, approved=False)
    session.add(proposal(waiting, "PENDING", BEFORE))
    rebuilt = await craft(session, REBUILT)
    await laid(session, rebuilt, BEFORE, approved=True)
    await laid(session, rebuilt, AFTER, approved=True)
    await laid(session, await craft(session, BAR), BEFORE, approved=True)
    built = {page.key: page.version for page in await built_before_round(session)}
    assert (built.get(f"craft:{OLD}"), built.get(f"craft:{SWAPPED}")) == (1, 1)
    assert not set(built) & {f"craft:{slug}" for slug in (NEW, SYSTEM, WAITING, REBUILT, BAR)}


async def test_the_task_is_listed_until_a_rebuild_waits_or_is_written_and_a_swap_is_no_rebuild(
    session: AsyncSession,
) -> None:
    old = await craft(session, OLD)
    await laid(session, old, BEFORE, approved=True)
    await store_document(session, document(OLD))
    await raise_page_upgrades(session, compose=QUIET)
    raised = await session.scalar(select(PageUpgrade.raisedAt).where(PageUpgrade.subjectSlug == OLD))
    assert raised is not None
    session.add(proposal(old, "PENDING", raised - timedelta(days=1)))
    await laid(session, old, AFTER, approved=False)
    (task,) = await listed(session)
    assert (task.key, task.prompt, task.count) == (f"UPGRADE_PAGE:craft:{OLD}", "deliver_page", 1)
    assert LINE in task.needed and "kalavigyan://skills/references/playbook.md" in task.needed
    assert await open_task(session, parse_task_key(task.key), site=SITE) == task
    rebuild = proposal(old, "PENDING", raised + timedelta(seconds=1))
    session.add(rebuild)
    await session.flush()
    assert await listed(session) == []
    rebuild.status, rebuild.reviewedAt = "REJECTED", NOW
    await session.flush()
    assert [task.key for task in await listed(session)] == [f"UPGRADE_PAGE:craft:{OLD}"]
    await laid(session, old, NOW, approved=True)
    assert await listed(session) == []


async def listed(session: AsyncSession) -> list[OpenTask]:
    filters = WorkFilters(craft_slug=OLD, kind="UPGRADE_PAGE")
    return list((await list_open_work(session, filters, Viewer(), site=SITE, now=NOW)).tasks)
