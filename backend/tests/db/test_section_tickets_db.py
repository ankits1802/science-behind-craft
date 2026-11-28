import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidInput
from app.models import SectionProposal, User
from app.research.page_proposals import PageBundle
from app.research.review_queue import QueueApproval, QueueRejection
from app.research.section_proposals import SectionTicket
from app.services.page_proposals import PageTools, propose_page
from app.services.review_queue_decisions import ItemRef, approve_item, reject_item
from app.services.section_tickets import followed_proposal

from .page_documents_seed import (
    ADMIN,
    CATEGORY_CLAIM,
    CRAFT_CLAIM,
    CRAFT_SLUG,
    CRAFT_TEXT,
    FAMILY_CLAIM,
    seed,
)
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=UTC)
SITE = "https://kalavigyan.example"
WRITER = uuid.UUID("5ec7e000-0000-4000-8000-000000000001")
OTHER = uuid.UUID("5ec7e000-0000-4000-8000-000000000002")
PROFESSOR = uuid.UUID("5ec7e000-0000-4000-8000-000000000003")
FAMILY_TEXT = "Printers across India print with carved wooden blocks."
CATEGORY_TEXT = "Textile crafts dye, print and weave cloth."
RESTATED = [(CRAFT_TEXT, CRAFT_CLAIM), (FAMILY_TEXT, FAMILY_CLAIM), (CATEGORY_TEXT, CATEGORY_CLAIM)]
REASON = "It retells the list without joining the facts."


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        for user_id, role in ((WRITER, "RESEARCHER"), (OTHER, "RESEARCHER"), (PROFESSOR, "PROFESSOR")):
            opened.add(
                User(id=user_id, name="Section follower", email=f"{user_id.hex}@example.org", role=role)
            )
        await opened.flush()
        yield opened


async def spent_nothing(kind: str) -> None:
    return None


def tools() -> PageTools:
    nothing: Any = None
    return PageTools(
        gates=nothing,
        fetcher=nothing,
        start_picture=nothing,
        spend=spent_nothing,
        origin="AGENT",
        site=SITE,
        judges=(),
    )


async def person(session: AsyncSession, user_id: uuid.UUID) -> User:
    found = await session.get(User, user_id)
    assert found is not None
    return found


async def proposed(
    session: AsyncSession, user_id: uuid.UUID, sentences: list[tuple[str, uuid.UUID]]
) -> uuid.UUID:
    written = [{"text": text, "claim_ids": [str(claim)]} for text, claim in sentences]
    body = PageBundle.model_validate(
        {
            "subject": {"kind": "craft", "slug": CRAFT_SLUG},
            "sections": [{"field": "CHEMISTRY", "sentences": written}],
        }
    )
    result = await propose_page(session, await person(session, user_id), body, tools=tools(), now=NOW)
    return uuid.UUID(str(result.parts[0].id))


async def followed(session: AsyncSession, user_id: uuid.UUID, proposal_id: uuid.UUID) -> SectionTicket:
    found = (await followed_proposal(session, await person(session, user_id), proposal_id)).root
    assert isinstance(found, SectionTicket)
    return found


async def test_the_proposer_follows_its_waiting_section_with_every_check_and_no_section_yet(
    session: AsyncSession,
) -> None:
    proposal_id = await proposed(session, WRITER, RESTATED)
    ticket = await followed(session, WRITER, proposal_id)
    assert (ticket.kind, ticket.status, ticket.field, ticket.subject.slug) == (
        "SECTION",
        "PENDING",
        "CHEMISTRY",
        CRAFT_SLUG,
    )
    assert [check.check for check in ticket.checks] == ["HELD", "FIELD", "SENTENCES", "STATED", "FAITHFUL"]
    assert all(check.passed and check.reasons for check in ticket.checks)
    assert [sentence.text for sentence in ticket.sentences] == [text for text, _ in RESTATED]
    assert (ticket.section, ticket.review_note, ticket.reviewed_at) == (None, None, None)
    assert ticket.message.startswith("Waiting for review")
    dumped = (await followed_proposal(session, await person(session, WRITER), proposal_id)).model_dump(
        mode="json", by_alias=True
    )
    assert (dumped["kind"], dumped["proposalId"]) == ("SECTION", str(proposal_id))


async def test_an_approved_section_names_the_published_section_it_became_and_the_reviewer_s_note(
    session: AsyncSession,
) -> None:
    proposal_id = await proposed(session, WRITER, RESTATED)
    note = QueueApproval(note="Joined in the order of the dyeing.")
    await approve_item(session, ItemRef("SECTIONS", proposal_id), await person(session, ADMIN), note, now=NOW)
    ticket = await followed(session, WRITER, proposal_id)
    assert (ticket.status, ticket.review_note, ticket.reviewed_at) == ("APPROVED", note.note, NOW)
    assert ticket.section is not None
    assert (ticket.section.version, ticket.section.status) == (2, "PUBLISHED")
    assert ticket.section.page_url is not None and ticket.section.page_url.endswith(f"/crafts/{CRAFT_SLUG}")
    assert ticket.message.startswith("Approved: it is the page's CHEMISTRY section now, version 2")


async def test_a_rejected_section_carries_the_reviewer_s_reason_and_no_section(session: AsyncSession) -> None:
    proposal_id = await proposed(session, WRITER, RESTATED)
    rejection = QueueRejection(reason=REASON)
    await reject_item(
        session, ItemRef("SECTIONS", proposal_id), await person(session, ADMIN), rejection, now=NOW
    )
    ticket = await followed(session, WRITER, proposal_id)
    assert (ticket.status, ticket.review_note, ticket.section) == ("REJECTED", REASON, None)
    assert ticket.message == f"Rejected by its reviewer: {REASON}"


async def test_a_refused_section_says_which_check_refused_it_and_why(session: AsyncSession) -> None:
    proposal_id = await proposed(session, WRITER, RESTATED[:2])
    ticket = await followed(session, WRITER, proposal_id)
    assert ticket.status == "REFUSED"
    refused = [check for check in ticket.checks if not check.passed]
    assert [check.check for check in refused] == ["SENTENCES"] and refused[0].reasons
    assert "the SENTENCES check refused the whole section" in ticket.message


async def test_a_professor_s_section_written_at_once_is_followed_as_approved(session: AsyncSession) -> None:
    proposal_id = await proposed(session, PROFESSOR, RESTATED)
    ticket = await followed(session, PROFESSOR, proposal_id)
    assert ticket.status == "APPROVED" and ticket.section is not None
    assert ticket.review_note is not None and "approved at once" in ticket.review_note


async def test_another_contributor_is_refused_and_an_admin_reads_any_section(session: AsyncSession) -> None:
    proposal_id = await proposed(session, WRITER, RESTATED)
    with pytest.raises(InvalidInput, match="No proposal of this account"):
        await followed_proposal(session, await person(session, OTHER), proposal_id)
    assert (await followed(session, ADMIN, proposal_id)).status == "PENDING"
    assert await session.get(SectionProposal, proposal_id) is not None


async def test_an_id_that_is_no_section_is_read_as_a_fact_proposal(session: AsyncSession) -> None:
    with pytest.raises(InvalidInput, match="propose_facts, propose_page and my_work give the ids"):
        await followed_proposal(session, await person(session, WRITER), uuid.UUID(int=7))
