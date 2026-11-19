import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, LayoutProposal, User
from app.research.layout_proposals import LayoutProposalDraft
from app.research.page_layout import LayoutWrite
from app.research.review_queue import LayoutItem, QueueApproval, QueueRejection, ReviewFilters
from app.services import review_queue_decisions as decisions
from app.services.page_layout_proposals import propose_layout
from app.services.page_layouts import LAYOUT_WRITTEN, page_layout, write_layout
from app.services.review_queue import QueueAdapters, list_review_queue
from app.services.review_queue_errors import DecisionConflict, OwnItem

from .page_documents_seed import ADMIN, CATEGORY_SLUG, CRAFT_SLUG, NOW, PICTURE, seed
from .review_queue_seed import TurnsOf
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

SITE = "https://kalavigyan.example"
ADAPTERS = QueueAdapters(objects=None, turns_of=TurnsOf())
HERO = {"ref": PICTURE, "chapter": "glance", "order": 1, "role": "HERO"}
BODY_UNIT = {"ref": "h-overview", "chapter": "glance", "order": 2, "role": "BODY"}


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        yield opened


async def person(session: AsyncSession, role: str) -> User:
    made = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:10]}@example.org",
        name=f"{role.title()} Layouts",
        role=role,
    )
    session.add(made)
    await session.flush()
    return made


def draft(
    base: int, *entries: dict[str, Any], kind: str = "craft", slug: str = CRAFT_SLUG
) -> LayoutProposalDraft:
    body = {
        "subject": {"kind": kind, "slug": slug},
        "baseVersion": base,
        "entries": list(entries),
        "note": "Hero first.",
    }
    return LayoutProposalDraft.model_validate(body)


async def proposed(session: AsyncSession, user: User, proposal: LayoutProposalDraft) -> uuid.UUID:
    result = await propose_layout(session, user, proposal, origin="AGENT", site=SITE, now=NOW)
    return result.proposal_id


async def layouts_queue(session: AsyncSession, viewer: User, **filters: Any) -> list[LayoutItem]:
    page = await list_review_queue(
        session, viewer, ReviewFilters(kind="LAYOUTS", **filters), adapters=ADAPTERS, now=NOW
    )
    return [item for item in page.items if isinstance(item, LayoutItem)]


async def actions(session: AsyncSession, target: uuid.UUID) -> list[str]:
    await session.flush()
    rows = await session.scalars(select(AuditLog.action).where(AuditLog.targetId == str(target)))
    return sorted(rows.all())


async def test_a_researcher_s_layout_waits_in_the_queue_with_what_it_changes(session: AsyncSession) -> None:
    researcher, admin = await person(session, "RESEARCHER"), await session.get(User, ADMIN)
    proposal_id = await proposed(session, researcher, draft(0, HERO))
    row = await session.get(LayoutProposal, proposal_id)
    assert (row.status, row.origin, row.baseVersion, row.layoutVersion) == ("PENDING", "AGENT", 0, None)
    assert await page_layout(session, "craft", CRAFT_SLUG) is None
    (item,) = await layouts_queue(session, admin)
    assert (item.id, item.origin, item.craft.slug, item.proposer.role) == (
        proposal_id,
        "AGENT",
        CRAFT_SLUG,
        "RESEARCHER",
    )
    review = item.layout
    assert (review.subject.slug, review.base_version, review.current_version, review.stale) == (
        CRAFT_SLUG,
        0,
        0,
        False,
    )
    assert [(change.ref, change.change) for change in review.changes] == [(PICTURE, "ADDED")]
    professor = await person(session, "PROFESSOR")
    assert (
        "LAYOUTS"
        not in (
            await list_review_queue(session, professor, ReviewFilters(), adapters=ADAPTERS, now=NOW)
        ).kinds
    )


async def test_approval_writes_the_next_layout_version_and_audits_both(session: AsyncSession) -> None:
    researcher, admin = await person(session, "RESEARCHER"), await session.get(User, ADMIN)
    proposal_id = await proposed(session, researcher, draft(0, HERO, BODY_UNIT))
    decided = await decisions.approve_item(
        session, decisions.ItemRef("LAYOUTS", proposal_id), admin, QueueApproval(note="Good."), now=NOW
    )
    assert (decided.kind, decided.status) == ("LAYOUTS", "APPROVED")
    layout = await page_layout(session, "craft", CRAFT_SLUG)
    assert layout is not None and (layout.version, [entry.ref for entry in layout.entries]) == (
        1,
        [PICTURE, "h-overview"],
    )
    row = await session.get(LayoutProposal, proposal_id)
    assert (row.status, row.reviewedById, row.reviewNote, row.layoutVersion) == (
        "APPROVED",
        ADMIN,
        "Good.",
        1,
    )
    assert await actions(session, proposal_id) == ["review.layout_approved"]
    written = await session.scalars(
        select(AuditLog.detail).where(AuditLog.action == LAYOUT_WRITTEN, AuditLog.actorId == ADMIN)
    )
    assert [detail["version"] for detail in written.all()] == [1]
    with pytest.raises(DecisionConflict, match="approved already"):
        await decisions.reject_item(
            session, decisions.ItemRef("LAYOUTS", proposal_id), admin, QueueRejection(reason="Late."), now=NOW
        )


async def test_a_layout_built_on_a_version_the_page_left_can_only_be_rejected(session: AsyncSession) -> None:
    researcher, admin = await person(session, "RESEARCHER"), await session.get(User, ADMIN)
    proposal_id = await proposed(session, researcher, draft(0, HERO))
    await write_layout(session, "craft", CRAFT_SLUG, LayoutWrite(base_version=0, entries=[]), actor=admin)
    (item,) = await layouts_queue(session, admin)
    assert (item.layout.current_version, item.layout.stale) == (1, True)
    with pytest.raises(DecisionConflict, match="version 1 now, not the version 0"):
        await decisions.approve_item(
            session, decisions.ItemRef("LAYOUTS", proposal_id), admin, QueueApproval(), now=NOW
        )
    rejected = await decisions.reject_item(
        session,
        decisions.ItemRef("LAYOUTS", proposal_id),
        admin,
        QueueRejection(reason="Built on an old version."),
        now=NOW,
    )
    assert rejected.status == "REJECTED"
    row = await session.get(LayoutProposal, proposal_id)
    assert (row.reviewNote, row.layoutVersion) == ("Built on an old version.", None)
    assert (await page_layout(session, "craft", CRAFT_SLUG)).version == 1


async def test_an_admin_s_own_layout_is_written_at_once_and_never_waits(session: AsyncSession) -> None:
    admin = await session.get(User, ADMIN)
    result = await propose_layout(
        session,
        admin,
        draft(0, BODY_UNIT, kind="category", slug=CATEGORY_SLUG),
        origin="CONTRIBUTION",
        site=SITE,
        now=NOW,
    )
    assert (result.outcome, result.version) == ("WRITTEN", 1)
    assert (await page_layout(session, "category", CATEGORY_SLUG)).version == 1
    other_admin = await person(session, "ADMIN")
    assert await layouts_queue(session, other_admin) == []
    with pytest.raises(OwnItem):
        await decisions.approve_item(
            session, decisions.ItemRef("LAYOUTS", result.proposal_id), admin, QueueApproval(), now=NOW
        )


async def test_a_category_layout_has_no_craft_and_the_craft_filter_leaves_it_out(
    session: AsyncSession,
) -> None:
    researcher, admin = await person(session, "RESEARCHER"), await session.get(User, ADMIN)
    proposal_id = await proposed(
        session, researcher, draft(0, BODY_UNIT, kind="category", slug=CATEGORY_SLUG)
    )
    (item,) = await layouts_queue(session, admin)
    assert (item.id, item.craft, item.layout.subject.kind) == (proposal_id, None, "category")
    assert await layouts_queue(session, admin, craft_slug=CRAFT_SLUG) == []
    assert await layouts_queue(session, admin, origin="CONTRIBUTION") == []
