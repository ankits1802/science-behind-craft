import uuid
from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import ComponentProposal, PageHold, PagePreview, User
from app.research.page_proposals import PageBundle
from app.research.page_render import DrawingReport, DrawnProblem
from app.services.open_work_subjects import subject_by_key
from app.services.page_holds import HoldPlace, hold_page
from app.services.page_preview import preview_page
from app.services.page_preview_links import UnknownPreview, issued_pass, pass_document, preview_token
from app.services.page_preview_pictures import pass_picture_file
from app.services.page_proposals import propose_page
from app.services.page_renders import drawing_refusal, record_drawing

from .page_documents_seed import CRAFT_SLUG, seed
from .test_page_bundles_db import NOW, SITE, SUBJECT, component, tools
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

MAKER = uuid.UUID("9e2a0000-0000-4000-8000-000000000001")
OTHER = uuid.UUID("9e2a0000-0000-4000-8000-000000000002")
LABEL = "page-docs-test-craft/chemistry/alum-print-table"
ICON = DrawnProblem(width=390, label=LABEL, problem="an icon of 24 units draws 239px wide")


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        for user_id in (MAKER, OTHER):
            opened.add(
                User(id=user_id, name="Page maker", email=f"{user_id.hex}@example.org", role="RESEARCHER")
            )
        await opened.flush()
        yield opened


def bundle() -> PageBundle:
    return PageBundle.model_validate({"subject": SUBJECT, "components": [component(LABEL)]})


def drawing(state: str, *problems: DrawnProblem) -> DrawingReport:
    return DrawingReport(state=state, widths=[390, 1440], problems=list(problems), images=[])


async def maker(session: AsyncSession, user_id: uuid.UUID = MAKER) -> User:
    found = await session.get(User, user_id)
    assert found is not None
    return found


async def drawn(
    session: AsyncSession, user: User, state: str, *problems: DrawnProblem, minutes: int = 0
) -> str:
    previewed = await preview_page(session, user, bundle(), site=SITE, now=NOW + timedelta(minutes=minutes))
    await record_drawing(session, user, previewed.preview_url, drawing(state, *problems), now=NOW)
    return previewed.preview_url


async def test_a_failed_drawing_is_kept_on_its_preview_with_its_problems(session: AsyncSession) -> None:
    user = await maker(session)
    await drawn(session, user, "FAILED", ICON)
    row = await session.scalar(select(PagePreview).where(PagePreview.userId == MAKER))
    assert row is not None and row.drawing == "FAILED"
    assert row.drawingProblems == [
        {"width": 390, "label": LABEL, "problem": "an icon of 24 units draws 239px wide"}
    ]


async def test_a_page_whose_latest_preview_failed_its_drawing_is_refused_and_nothing_is_proposed_or_held(
    session: AsyncSession,
) -> None:
    user = await maker(session)
    await drawn(session, user, "FAILED", ICON)
    with pytest.raises(InvalidInput) as refused:
        await propose_page(session, user, bundle(), tools=tools(), now=NOW)
    assert "failed its drawing checks (rule 28 of the page checklist)" in str(refused.value)
    assert f"390 px, {LABEL}: an icon of 24 units draws 239px wide" in str(refused.value)
    with pytest.raises(InvalidInput, match="failed its drawing checks"):
        await hold_page(session, user, bundle(), None, HoldPlace(site=SITE, client_name=None, now=NOW))
    proposals = select(func.count()).select_from(ComponentProposal).where(ComponentProposal.label == LABEL)
    assert await session.scalar(proposals) == 0
    assert (
        await session.scalar(select(func.count()).select_from(PageHold).where(PageHold.userId == MAKER)) == 0
    )


async def test_a_later_preview_that_does_not_fail_lets_the_page_through_and_another_account_is_not_held_back(
    session: AsyncSession,
) -> None:
    user, other = await maker(session), await maker(session, OTHER)
    subject = await subject_by_key(session, "craft", CRAFT_SLUG)
    await drawn(session, user, "FAILED", ICON)
    assert await drawing_refusal(session, other.id, subject, now=NOW) is None
    await drawn(session, user, "UNMADE", minutes=1)
    assert await drawing_refusal(session, user.id, subject, now=NOW + timedelta(minutes=1)) is None
    await drawn(session, user, "FAILED", ICON, minutes=2)
    assert await drawing_refusal(session, user.id, subject, now=NOW + timedelta(minutes=2)) is not None
    await drawn(session, user, "CHECKED", minutes=3)
    assert await drawing_refusal(session, user.id, subject, now=NOW + timedelta(minutes=3)) is None


async def test_the_renderer_s_pass_reads_its_own_preview_for_two_minutes_and_nothing_else(
    session: AsyncSession,
) -> None:
    user = await maker(session)
    first = await drawn(session, user, "UNMADE")
    second = await drawn(session, user, "UNMADE", minutes=1)
    render_pass = issued_pass(first, user, now=NOW)
    token = preview_token(first)
    document = await pass_document(session, render_pass, token, now=NOW)
    assert document["subjectSlug"] == CRAFT_SLUG
    refusals = [
        (render_pass, token, NOW + timedelta(minutes=3)),
        (token, token, NOW),
        (issued_pass(second, user, now=NOW), token, NOW),
    ]
    for given, read, when in refusals:
        with pytest.raises(UnknownPreview):
            await pass_document(session, given, read, now=when)
    assert await pass_picture_file(session, render_pass, uuid.uuid4(), now=NOW) is None
    assert await pass_picture_file(session, token, uuid.uuid4(), now=NOW) is None
