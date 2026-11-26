import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DesignReadCache, LayoutProposal, PagePreview, User
from app.research.design_critique import DesignCritique, DesignNote
from app.research.design_read import READ, DesignRead
from app.research.page_proposals import PageBundle
from app.services.page_critique import attach_critique, critiqued, latest_critique
from app.services.page_design_read import CACHE_DAYS, cached_read, store_read
from app.services.page_preview import preview_page
from app.services.page_proposals import propose_page
from app.services.page_reviews import DrawnPreview
from app.services.review_queue_layouts import layout_items

from .page_documents_seed import CRAFT_SLUG, seed
from .test_page_bundles_db import FACT_PART, NOW, SITE, SUBJECT, component, tools
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

MAKER = uuid.UUID("9e3a0000-0000-4000-8000-000000000001")
LABEL = "page-docs-test-craft/chemistry/alum-print-table"
KEY = "a" * 64
OTHER_KEY = "b" * 64
NOTE = DesignNote(chapter="opening", where="the masthead", problem="No plate.", fix="Set the dye plate.")
READING = DesignRead(
    state=READ,
    verdict="The opening needs its plate.",
    notes=[NOTE],
    chapters=["opening"],
    provider="ANTHROPIC",
    model="claude-opus-5-5",
    cost_usd=Decimal("0.214"),
)
CRITIQUE = DesignCritique(verdict="The making chapter is a wall of prose.", notes=[NOTE])


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        opened.add(User(id=MAKER, name="Page maker", email=f"{MAKER.hex}@example.org", role="RESEARCHER"))
        await opened.flush()
        yield opened


async def maker(session: AsyncSession) -> User:
    found = await session.get(User, MAKER)
    assert found is not None
    return found


def bundle() -> PageBundle:
    return PageBundle.model_validate(
        {"subject": SUBJECT, "facts": [FACT_PART], "components": [component(LABEL)]}
    )


async def test_a_read_is_kept_by_its_pictures_key_and_found_again_at_no_cost(session: AsyncSession) -> None:
    await store_read(session, KEY, READING, now=NOW)
    await store_read(session, KEY, READING.model_copy(update={"verdict": "A second read."}), now=NOW)
    found = await cached_read(session, KEY)
    assert found is not None and found.verdict == READING.verdict and found.notes == [NOTE]
    assert (found.cached, found.cost_usd) == (True, Decimal(0))
    assert await cached_read(session, OTHER_KEY) is None
    row = await session.get(DesignReadCache, KEY)
    assert row is not None and row.costUsd == Decimal("0.214000") and row.model == "claude-opus-5-5"


async def test_a_read_older_than_the_cache_s_days_is_cleared_when_the_next_is_kept(
    session: AsyncSession,
) -> None:
    await store_read(session, KEY, READING, now=NOW - timedelta(days=CACHE_DAYS + 1))
    await store_read(session, OTHER_KEY, READING, now=NOW)
    assert await cached_read(session, KEY) is None
    assert await session.scalar(select(func.count()).select_from(DesignReadCache)) == 1


async def test_the_latest_critique_rides_with_the_layout_to_the_review_queue(session: AsyncSession) -> None:
    user = await maker(session)
    critiqued_preview = await preview_page(session, user, bundle(), site=SITE, now=NOW)
    await critiqued(session, user, critiqued_preview, DrawnPreview(report=None), critique=CRITIQUE, now=NOW)
    plain = await preview_page(session, user, bundle(), site=SITE, now=NOW + timedelta(minutes=5))
    await critiqued(session, user, plain, DrawnPreview(report=None), critique=None, now=NOW)
    kept = await session.scalar(select(PagePreview.critique).where(PagePreview.critique.is_not(None)))
    assert kept == CRITIQUE.model_dump(mode="json")
    subject = ("craft", CRAFT_SLUG)
    assert await latest_critique(session, user.id, subject, now=NOW + timedelta(minutes=6)) == CRITIQUE
    assert await latest_critique(session, user.id, subject, now=NOW + timedelta(days=2)) is None
    layout = PageBundle.model_validate({"subject": SUBJECT, "layout": {"baseVersion": 0, "entries": []}})
    result = await propose_page(session, user, layout, tools=tools(), now=NOW)
    await attach_critique(session, user, result, now=NOW + timedelta(minutes=6))
    proposal = await session.scalar(select(LayoutProposal))
    assert proposal is not None and proposal.critique == CRITIQUE.model_dump(mode="json")
    (rendered,) = await layout_items(session, [proposal.id])
    assert rendered.item.layout.critique == CRITIQUE
