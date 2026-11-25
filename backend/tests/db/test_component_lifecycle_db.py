import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput, Refused
from app.models import AuditLog, ComponentProposal, KnowledgePiece, KnowledgePieceUnlink
from app.research.own_proposals import ComponentProposalBody
from app.research.page_layout import PageLayoutEntry
from app.research.page_proposals import PageBundle
from app.research.staged_reviews import ConfirmedItem, StagedConfirmation, StagedDecision
from app.services import own_proposals
from app.services.component_library import library_components
from app.services.component_lifecycle import live_piece, retirable_piece, take_off_pages, withdraw_registered
from app.services.component_proposals import propose_component
from app.services.open_work_subjects import craft_subject
from app.services.page_layouts import layout_of, store_layout
from app.services.page_proposals import propose_page
from app.services.review_queue_components import approve_component
from app.services.staged_review_confirm import confirm_batch
from app.services.staged_reviews import stage_decisions

from .component_lifecycle_seed import (
    ADMIN,
    NEW,
    NOW,
    OWN,
    OWN_PROPOSAL,
    PROPOSER,
    STEWARD,
    STRANGER,
    lifecycle_seed,
    person,
    replacement,
)
from .page_documents_seed import BARE_SLUG, CONCEPT_PLAYER, CRAFT_SLUG
from .test_page_bundles_db import tools
from .test_staged_reviews_db import caller_of
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

WHY = "It cites only another craft's facts on this page."
NOT_YOURS = "Only the proposer of"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await lifecycle_seed(opened)
        yield opened


async def labels_on_page(session: AsyncSession) -> list[str]:
    return [component.label for component in (await library_components(session, slug=CRAFT_SLUG)).components]


async def hidden(session: AsyncSession, label: str) -> tuple[Any, Any]:
    row = (
        await session.execute(
            select(KnowledgePiece.hiddenAt, KnowledgePiece.hiddenById).where(KnowledgePiece.label == label)
        )
    ).one()
    return row.hiddenAt, row.hiddenById


async def removals(session: AsyncSession) -> set[tuple[Any, Any, Any]]:
    rows = await session.scalars(select(AuditLog).where(AuditLog.action == "component.removed"))
    return {(row.actorId, row.detail["label"], row.detail["page"]) for row in rows.all()}


async def piece_ids(session: AsyncSession) -> dict[str, uuid.UUID]:
    rows = await session.execute(
        select(KnowledgePiece.label, KnowledgePiece.id).where(
            KnowledgePiece.label.in_([OWN, NEW, CONCEPT_PLAYER])
        )
    )
    return {str(label): piece_id for label, piece_id in rows.tuples().all()}


async def test_the_proposer_takes_a_registered_component_off_every_page_kept_in_the_record_and_audited(
    session: AsyncSession,
) -> None:
    proposer = await person(session, PROPOSER)
    assert OWN in await labels_on_page(session)
    mine = {item.label: item for item in (await own_proposals.own_proposals(session, proposer)).items}
    assert (mine[OWN].state, mine[OWN].registered) == ("APPROVED", True)
    withdrawn = await own_proposals.withdraw_component(session, proposer, OWN_PROPOSAL, now=NOW)
    assert (withdrawn.item.state, withdrawn.item.registered) == ("WITHDRAWN", False)
    assert CRAFT_SLUG in withdrawn.owners.crafts
    assert await hidden(session, OWN) == (NOW, PROPOSER)
    assert OWN not in await labels_on_page(session)
    assert await removals(session) == {(PROPOSER, OWN, None)}
    stored = await session.scalar(
        select(ComponentProposal.status).where(ComponentProposal.id == OWN_PROPOSAL)
    )
    assert stored == "WITHDRAWN"


async def test_only_the_proposer_or_an_admin_may_take_it_off_its_pages_at_once_not_a_steward(
    session: AsyncSession,
) -> None:
    stranger = await person(session, STRANGER)
    with pytest.raises(Refused, match=NOT_YOURS):
        await withdraw_registered(session, stranger, OWN, reason=WHY, now=NOW)
    with pytest.raises(own_proposals.UnknownProposal):
        await own_proposals.withdraw_component(session, stranger, OWN_PROPOSAL, now=NOW)
    for refused in (STRANGER, STEWARD):
        with pytest.raises(Refused, match=NOT_YOURS):
            await retirable_piece(session, await person(session, refused), OWN)
    for allowed in (PROPOSER, ADMIN):
        assert (await retirable_piece(session, await person(session, allowed), OWN)).label == OWN
    assert await hidden(session, OWN) == (None, None) and await removals(session) == set()


async def test_a_bundle_s_withdrawal_takes_the_component_off_and_a_stranger_s_is_refused(
    session: AsyncSession,
) -> None:
    bundle = PageBundle.model_validate(
        {"subject": {"kind": "craft", "slug": CRAFT_SLUG}, "withdrawals": [{"label": OWN, "reason": WHY}]}
    )
    (refused,) = (
        await propose_page(session, await person(session, STRANGER), bundle, tools=tools(), now=NOW)
    ).parts
    assert (refused.part, refused.outcome) == ("withdrawal", "REFUSED") and refused.message.startswith(
        NOT_YOURS
    )
    (taken,) = (
        await propose_page(session, await person(session, PROPOSER), bundle, tools=tools(), now=NOW)
    ).parts
    assert (taken.part, taken.outcome, taken.status) == ("withdrawal", "ACCEPTED", "WITHDRAWN")
    assert taken.message.startswith(f"Withdrawn: {OWN} is off every page")
    assert await hidden(session, OWN) == (NOW, PROPOSER)


async def test_approving_a_replacement_retires_the_old_component_from_the_page_s_layout_in_the_same_change(
    session: AsyncSession,
) -> None:
    page = await craft_subject(session, CRAFT_SLUG)
    await store_layout(
        session, page, [PageLayoutEntry(ref=OWN, chapter="chemistry", order=1, role="FIGURE")], actor=None
    )
    stranger_body = ComponentProposalBody.model_validate(
        replacement(label="page-docs-test-craft/chemistry/alum-other")
    )
    with pytest.raises(Refused, match=NOT_YOURS):
        await propose_component(session, await person(session, STRANGER), stranger_body, now=NOW)
    body = ComponentProposalBody.model_validate(replacement())
    stored = await propose_component(session, await person(session, PROPOSER), body, now=NOW)
    assert (stored.outcome, stored.status) == ("STORED", "PENDING")
    before = await layout_of(session, page)
    assert before is not None and (before.version, [e.ref for e in before.entries]) == (1, [OWN])
    assert stored.proposal_id is not None
    decided = await approve_component(
        session, stored.proposal_id, await person(session, ADMIN), note=None, now=NOW
    )
    assert decided.status == "APPROVED"
    after = await layout_of(session, page)
    assert after is not None and (after.version, [(e.ref, e.chapter, e.order) for e in after.entries]) == (
        2,
        [(NEW, "chemistry", 1)],
    )
    pieces = await piece_ids(session)
    superseded = await session.scalar(
        select(KnowledgePiece.supersededById).where(KnowledgePiece.label == OWN)
    )
    assert superseded == pieces[NEW] and OWN not in await labels_on_page(session)
    audit = await session.scalar(select(AuditLog).where(AuditLog.action == "component.replaced"))
    assert audit is not None and audit.actorId == ADMIN
    assert (audit.detail["label"], audit.detail["by"], audit.detail["layouts"]) == (OWN, NEW, 1)


def removal(piece_id: uuid.UUID, **more: str) -> StagedDecision:
    return StagedDecision.model_validate(
        {"kind": "COMPONENTS", "id": piece_id, "action": "remove", "reason": WHY, **more}
    )


async def test_an_admin_s_staged_removal_changes_nothing_until_a_person_confirms_it(
    session: AsyncSession,
) -> None:
    admin = await person(session, ADMIN)
    caller = await caller_of(session, admin)
    ids = await piece_ids(session)
    asked = [removal(ids[OWN]), removal(ids[CONCEPT_PLAYER], craft=CRAFT_SLUG)]
    staged = await stage_decisions(session, asked, caller, now=NOW)
    assert staged.refused == [] and staged.batch is not None
    assert [item.label for item in staged.items] == [
        f"Remove Plain alum table ({OWN}) from every page",
        f"Remove Title of {CONCEPT_PLAYER} ({CONCEPT_PLAYER}) from the page of {CRAFT_SLUG}",
    ]
    assert await hidden(session, OWN) == (None, None) and await removals(session) == set()
    assert await session.scalar(select(func.count()).select_from(KnowledgePieceUnlink)) == 0
    chosen = [
        ConfirmedItem(id=staged.items[0].id, action="remove", reason=WHY),
        ConfirmedItem(id=staged.items[1].id, action="remove", reason=WHY, craft=CRAFT_SLUG),
    ]
    confirmed = await confirm_batch(
        session, staged.batch.id, StagedConfirmation(items=chosen), admin, now=NOW
    )
    assert [item.state for item in staged.items] == ["APPLIED", "APPLIED"]
    assert CRAFT_SLUG in confirmed.owners.crafts
    assert await hidden(session, OWN) == (NOW, ADMIN)
    assert await hidden(session, CONCEPT_PLAYER) == (None, None)
    on_page = await labels_on_page(session)
    assert OWN not in on_page and CONCEPT_PLAYER not in on_page
    assert await removals(session) == {(ADMIN, OWN, None), (ADMIN, CONCEPT_PLAYER, f"craft:{CRAFT_SLUG}")}


async def test_a_stranger_is_told_who_takes_a_component_off_at_once_and_that_a_steward_may_ask(
    session: AsyncSession,
) -> None:
    with pytest.raises(Refused) as refused:
        await retirable_piece(session, await person(session, STRANGER), OWN)
    assert refused.value.message == (
        f"Only the proposer of {OWN} or an Admin may take it off its pages or replace it at once; "
        "a steward of its craft may ask."
    )
    assert (await retirable_piece(session, await person(session, PROPOSER), OWN)).label == OWN


async def test_a_one_page_removal_is_refused_on_a_page_that_does_not_draw_the_component(
    session: AsyncSession,
) -> None:
    admin, piece = await person(session, ADMIN), await live_piece(session, OWN)
    elsewhere = await craft_subject(session, BARE_SLUG)
    with pytest.raises(InvalidInput, match=f"{OWN} is not on {elsewhere.name}'s page"):
        await take_off_pages(session, admin, piece, page=elsewhere, reason=WHY, now=NOW)
    page = await craft_subject(session, CRAFT_SLUG)
    taken = await take_off_pages(session, admin, piece, page=page, reason=WHY, now=NOW)
    assert CRAFT_SLUG in taken.owners.crafts
    assert await removals(session) == {(ADMIN, OWN, f"{page.kind}:{CRAFT_SLUG}")}
