import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput, Refused
from app.models import AuditLog, KnowledgePiece, StagedReview, StagedReviewItem, User
from app.research.own_proposals import ComponentProposalBody
from app.research.page_drafts import DraftAddition
from app.research.page_proposals import PageBundle, PageSubject
from app.research.staged_reviews import ConfirmedItem, StagedConfirmation
from app.services.component_lifecycle import withdraw_registered
from app.services.component_proposals import propose_component
from app.services.page_drafts import add_to_draft, create_draft, held_parts
from app.services.page_proposals import propose_page
from app.services.review_queue_errors import NotYourQueue
from app.services.staged_review_confirm import confirm_batch
from app.services.stewardship import adopt_craft

from .component_lifecycle_seed import ADMIN, NOW, OWN, SITE, STRANGER, lifecycle_seed, person, replacement
from .page_documents_seed import BARE_SLUG, CRAFT_SLUG
from .test_page_bundles_db import tools
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

WHY = "It cites only another craft's facts on this page."
NOT_YOURS = "Only the proposer of"
ASKED = f"Asked: {OWN} stays on its pages until an Admin confirms its withdrawal"
PROFESSOR = uuid.UUID("9e1f0000-0000-4000-8000-000000000004")


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await lifecycle_seed(opened)
        yield opened


def withdrawal(slug: str = CRAFT_SLUG, reason: str | None = WHY) -> PageBundle:
    return PageBundle.model_validate(
        {"subject": {"kind": "craft", "slug": slug}, "withdrawals": [{"label": OWN, "reason": reason}]}
    )


async def steward(session: AsyncSession, user_id: uuid.UUID = STRANGER) -> User:
    account = await person(session, user_id)
    await adopt_craft(session, account, CRAFT_SLUG, site=SITE, now=NOW)
    return account


async def hidden(session: AsyncSession) -> tuple[Any, Any]:
    row = (
        await session.execute(
            select(KnowledgePiece.hiddenAt, KnowledgePiece.hiddenById).where(KnowledgePiece.label == OWN)
        )
    ).one()
    return row.hiddenAt, row.hiddenById


async def removals(session: AsyncSession) -> set[tuple[Any, Any]]:
    rows = await session.scalars(select(AuditLog).where(AuditLog.action == "component.removed"))
    return {(row.actorId, row.detail["label"]) for row in rows.all()}


async def test_a_stranger_who_adopts_the_craft_cannot_take_its_component_off_but_asks_an_admin(
    session: AsyncSession,
) -> None:
    adopted = await steward(session)
    with pytest.raises(Refused, match=NOT_YOURS):
        await withdraw_registered(session, adopted, OWN, reason=WHY, now=NOW)
    (asked,) = (await propose_page(session, adopted, withdrawal(), tools=tools(), now=NOW)).parts
    assert (asked.part, asked.outcome, asked.status, asked.id) == ("withdrawal", "ACCEPTED", "STAGED", None)
    assert asked.message.startswith(ASKED)
    assert await hidden(session) == (None, None) and await removals(session) == set()
    (again,) = (await propose_page(session, adopted, withdrawal(), tools=tools(), now=NOW)).parts
    assert (again.outcome, again.message) == (
        "REFUSED",
        "This change already waits for an Admin's confirmation on the Review page.",
    )
    (thin,) = (
        await propose_page(session, adopted, withdrawal(reason="Not good"), tools=tools(), now=NOW)
    ).parts
    assert thin.outcome == "REFUSED" and thin.message.startswith(f"{OWN} was proposed by another account")


async def test_a_steward_s_request_takes_the_component_off_only_when_an_admin_confirms_it(
    session: AsyncSession,
) -> None:
    adopted = await steward(session)
    await propose_page(session, adopted, withdrawal(), tools=tools(), now=NOW)
    batch = await session.scalar(select(StagedReview).where(StagedReview.proposerId == STRANGER))
    assert batch is not None and batch.clientName == "propose_page over MCP"
    (item,) = await session.scalars(select(StagedReviewItem).where(StagedReviewItem.batchId == batch.id))
    assert (item.kind, item.action, item.label) == (
        "COMPONENTS",
        "remove",
        f"Remove Plain alum table ({OWN}) from every page",
    )
    chosen = StagedConfirmation(items=[ConfirmedItem(id=item.id, action="remove", reason=WHY)])
    with pytest.raises(NotYourQueue):
        await confirm_batch(session, batch.id, chosen, adopted, now=NOW)
    assert await hidden(session) == (None, None)
    await confirm_batch(session, batch.id, chosen, await person(session, ADMIN), now=NOW)
    assert item.state == "APPLIED" and await hidden(session) == (NOW, ADMIN)
    assert await removals(session) == {(ADMIN, OWN)}


async def test_an_admin_still_withdraws_at_once_but_only_in_a_bundle_of_a_page_that_places_it(
    session: AsyncSession,
) -> None:
    admin = await person(session, ADMIN)
    (elsewhere,) = (await propose_page(session, admin, withdrawal(BARE_SLUG), tools=tools(), now=NOW)).parts
    assert elsewhere.outcome == "REFUSED" and elsewhere.message.startswith(f"{OWN} is not on")
    (taken,) = (await propose_page(session, admin, withdrawal(), tools=tools(), now=NOW)).parts
    assert (taken.outcome, taken.status) == ("ACCEPTED", "WITHDRAWN")
    assert await hidden(session) == (NOW, ADMIN) and await removals(session) == {(ADMIN, OWN)}
    assert await session.scalar(select(StagedReview.id).where(StagedReview.proposerId == ADMIN)) is None


async def test_a_draft_holds_a_steward_s_withdrawal_with_its_reason_and_refuses_a_stranger_s(
    session: AsyncSession,
) -> None:
    stranger = await person(session, STRANGER)
    draft = await create_draft(session, stranger, PageSubject(kind="craft", slug=CRAFT_SLUG), now=NOW)
    added = DraftAddition.model_validate({"withdrawals": [{"label": OWN, "reason": WHY}]})
    with pytest.raises(Refused, match=NOT_YOURS):
        await add_to_draft(session, stranger, draft.id, added, now=NOW)
    await adopt_craft(session, stranger, CRAFT_SLUG, site=SITE, now=NOW)
    short = DraftAddition.model_validate({"withdrawals": [{"label": OWN}]})
    with pytest.raises(InvalidInput, match="a steward's withdrawal of it waits for an Admin"):
        await add_to_draft(session, stranger, draft.id, short, now=NOW)
    held = await add_to_draft(session, stranger, draft.id, added, now=NOW)
    assert [(gone.label, gone.reason) for gone in held_parts(held).withdrawals] == [(OWN, WHY)]


async def test_a_steward_s_replacement_waits_for_review_even_from_a_professor_and_an_admin_s_does_not(
    session: AsyncSession,
) -> None:
    session.add(User(id=PROFESSOR, name="Professor", email=f"{PROFESSOR.hex}@example.org", role="PROFESSOR"))
    await session.flush()
    professor = await steward(session, PROFESSOR)
    body = ComponentProposalBody.model_validate(replacement())
    waiting = await propose_component(session, professor, body, now=NOW)
    assert (waiting.outcome, waiting.status) == ("STORED", "PENDING")
    superseded = select(KnowledgePiece.supersededById).where(KnowledgePiece.label == OWN)
    assert await session.scalar(superseded) is None
    own = ComponentProposalBody.model_validate(
        replacement(label="page-docs-test-craft/chemistry/alum-admin-record")
    )
    at_once = await propose_component(session, await person(session, ADMIN), own, now=NOW)
    assert (at_once.outcome, at_once.status) == ("STORED", "APPROVED")
    assert await session.scalar(superseded) is not None
