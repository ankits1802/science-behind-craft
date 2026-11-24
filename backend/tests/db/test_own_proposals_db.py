import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Refused
from app.models import AuditLog, CandidateCheck, Claim, ComponentProposal, Concept, ReviewEvent, User
from app.research.knowledge_writes import FactProposal
from app.research.own_proposals import ComponentProposalBody, TermsAcceptance
from app.research.retrieval import HIDDEN_CLAIM_STATUSES
from app.services import own_proposals
from app.services.component_proposals import propose_component
from app.services.fact_proposals import ProposalAdapters, propose_fact

from ..craft_fixtures import unit
from ..knowledge_writes.fakes import PAGE_URL, QUOTE, STATEMENT, FakeEmbedder, FakeFetcher, FakeJudge, page
from .open_work_seed import CRAFT, NOW, OTHER, PROFESSOR, RESEARCHER, SLUG, WHAT_IF, opened_session

pytestmark = pytest.mark.db

CRAFT_CONCEPT = uuid.UUID("0b000000-0000-4000-8000-000000000001")
WAITS, LIVE, REFUSED, REJECTED, OTHERS = (
    uuid.UUID(f"0b000000-0000-4000-8000-0000000000{n}") for n in range(11, 16)
)
TESTIMONY = uuid.UUID("0b000000-0000-4000-8000-000000000017")
PENDING_LABEL = "open-work-test-craft/chemistry/zircovane-lattice"
REJECTED_LABEL = "open-work-test-craft/history/zircovane-trade-map"
REVIEWER_REASON = "The GI record gives a different count of dips."
COMPONENT_REASON = "A map of the zircovane trade already waits to be built."


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in opened_session():
        opened.add(
            Concept(id=CRAFT_CONCEPT, craftId=CRAFT, type="ARTISAN_ACTION", name="Open Work Test Craft")
        )
        await opened.flush()
        await _seed_facts(opened)
        await _seed_components(opened)
        yield opened


async def _seed_facts(session: AsyncSession) -> None:
    session.add_all(
        [
            _fact(WAITS, "DRAFT", minutes=1),
            _fact(LIVE, "IN_REVIEW", minutes=2),
            _fact(REFUSED, "REJECTED", minutes=3),
            _fact(REJECTED, "REJECTED", minutes=4),
            _fact(OTHERS, "DRAFT", minutes=5, proposer=OTHER),
            _fact(TESTIMONY, "APPROVED", minutes=6, origin="ARTISAN"),
        ]
    )
    await session.flush()
    session.add_all(
        [
            _check(REFUSED, "QUOTES", passed=False, reasons=["the quote was not found on the page"]),
            _check(REJECTED, "QUOTES", passed=True, reasons=["every quote was found"]),
            _check(REJECTED, "SOURCE", passed=True, reasons=["a C source"]),
            ReviewEvent(
                claimId=REJECTED, actorId=RESEARCHER, actorKind="USER", toStatus="DRAFT", note="waits"
            ),
            ReviewEvent(
                claimId=REJECTED,
                actorId=PROFESSOR,
                actorKind="USER",
                toStatus="REJECTED",
                note=REVIEWER_REASON,
            ),
        ]
    )
    await session.flush()


async def _seed_components(session: AsyncSession) -> None:
    session.add_all(
        [
            _component(PENDING_LABEL, "PENDING", minutes=7),
            _component(REJECTED_LABEL, "REJECTED", minutes=8, reviewedAt=NOW, reviewNote=COMPONENT_REASON),
        ]
    )
    await session.flush()


def _fact(
    claim_id: uuid.UUID,
    status: str,
    *,
    minutes: int,
    proposer: uuid.UUID = RESEARCHER,
    origin: str = "CONTRIBUTION",
) -> Claim:
    return Claim(
        id=claim_id,
        subjectType="CONCEPT",
        subjectId=CRAFT_CONCEPT,
        predicate="states",
        text=f"The zircovane cloth is dipped {minutes} times, a test statement of twenty characters.",
        evidenceLevel="PROVISIONAL",
        origin=origin,
        status=status,
        createdById=proposer,
        createdByKind="USER",
        field="PROCESS",
        createdAt=NOW + timedelta(minutes=minutes),
    )


def _check(claim_id: uuid.UUID, gate: str, *, passed: bool, reasons: list[str]) -> CandidateCheck:
    return CandidateCheck(claimId=claim_id, gate=gate, passed=passed, reasons=reasons, checkedAt=NOW)


def _component(label: str, status: str, *, minutes: int, **changes: Any) -> ComponentProposal:
    return ComponentProposal(
        proposerId=RESEARCHER,
        label=label,
        title=f"Zircovane {label.rsplit('/', 1)[-1]}",
        description="A component proposed in the test, described at more than forty characters.",
        kind="molecule_3d",
        field="CHEMISTRY",
        craftId=CRAFT,
        subjects=[{"kind": "CRAFT", "key": SLUG}],
        status=status,
        createdAt=NOW + timedelta(minutes=minutes),
        **changes,
    )


async def person(session: AsyncSession, user_id: uuid.UUID) -> User:
    found = await session.get(User, user_id)
    assert found is not None
    return found


async def test_the_list_holds_only_the_person_s_own_proposals_newest_first_with_what_happened(
    session: AsyncSession,
) -> None:
    listed = (await own_proposals.own_proposals(session, await person(session, RESEARCHER))).items
    assert [(item.kind, item.state) for item in listed] == [
        ("COMPONENT", "REJECTED"),
        ("COMPONENT", "WAITING"),
        ("FACT", "REJECTED"),
        ("FACT", "REFUSED"),
        ("FACT", "PUBLISHED"),
        ("FACT", "WAITING"),
    ]
    by_id = {item.id: item for item in listed}
    assert by_id[REFUSED].reasons == ["the quote was not found on the page"]
    assert [gate.gate for gate in by_id[REFUSED].gates] == ["QUOTES"]
    assert by_id[REJECTED].reasons == [REVIEWER_REASON]
    assert (by_id[WAITS].subject_name, by_id[WAITS].craft_slug) == ("Open Work Test Craft", SLUG)
    assert listed[0].reasons == [COMPONENT_REASON]
    assert (listed[1].label, listed[1].subject_name) == (PENDING_LABEL, "Open Work Test Craft")


async def test_a_waiting_fact_is_withdrawn_and_stays_hidden(session: AsyncSession) -> None:
    researcher = await person(session, RESEARCHER)
    item = await own_proposals.withdraw_fact(session, researcher, WAITS)
    assert (item.state, item.status) == ("WITHDRAWN", "WITHDRAWN")
    assert await session.scalar(select(Claim.status).where(Claim.id == WAITS)) == "WITHDRAWN"
    assert "WITHDRAWN" in HIDDEN_CLAIM_STATUSES
    events = (await session.scalars(select(ReviewEvent).where(ReviewEvent.claimId == WAITS))).all()
    assert [(event.actorId, event.fromStatus, event.toStatus) for event in events] == [
        (RESEARCHER, "DRAFT", "WITHDRAWN")
    ]


async def test_a_published_fact_stays_published_because_consent_cannot_be_revoked(
    session: AsyncSession,
) -> None:
    with pytest.raises(Refused, match="consent cannot be revoked"):
        await own_proposals.withdraw_fact(session, await person(session, RESEARCHER), LIVE)
    assert await session.scalar(select(Claim.status).where(Claim.id == LIVE)) == "IN_REVIEW"


async def test_another_person_s_fact_or_a_testimony_is_not_the_person_s_to_withdraw(
    session: AsyncSession,
) -> None:
    researcher = await person(session, RESEARCHER)
    for claim_id in (OTHERS, TESTIMONY):
        with pytest.raises(own_proposals.UnknownProposal):
            await own_proposals.withdraw_fact(session, researcher, claim_id)
    assert await session.scalar(select(Claim.status).where(Claim.id == OTHERS)) == "DRAFT"


async def test_a_withdrawn_component_frees_its_label_and_a_reviewed_one_stays(session: AsyncSession) -> None:
    researcher = await person(session, RESEARCHER)
    pending = await session.scalar(
        select(ComponentProposal.id).where(ComponentProposal.label == PENDING_LABEL)
    )
    rejected = await session.scalar(
        select(ComponentProposal.id).where(ComponentProposal.label == REJECTED_LABEL)
    )
    withdrawn = await own_proposals.withdraw_component(session, researcher, pending, now=NOW)
    assert (withdrawn.item.state, withdrawn.item.registered, withdrawn.owners.empty) == (
        "WITHDRAWN",
        False,
        True,
    )
    with pytest.raises(Refused, match="nothing to withdraw"):
        await own_proposals.withdraw_component(session, researcher, rejected, now=NOW)
    with pytest.raises(own_proposals.UnknownProposal):
        await own_proposals.withdraw_component(session, await person(session, OTHER), pending, now=NOW)
    again = ComponentProposalBody.model_validate({**_component_body(), "label": PENDING_LABEL})
    stored = await propose_component(session, researcher, again, now=NOW)
    assert (stored.outcome, stored.label) == ("STORED", PENDING_LABEL)


async def test_the_terms_are_accepted_once_per_version_and_a_proposal_needs_them(
    session: AsyncSession,
) -> None:
    researcher = await person(session, RESEARCHER)
    assert (await own_proposals.terms_status(session, researcher)).accepted_at is None
    body = ComponentProposalBody.model_validate(_component_body())
    with pytest.raises(Refused, match="Accept the contribution terms, version 2026-11-19"):
        await own_proposals.propose_on_site(session, researcher, body, now=NOW)
    first = await own_proposals.accept_terms(session, researcher, TermsAcceptance(version="2026-11-19"))
    again = await own_proposals.accept_terms(session, researcher, TermsAcceptance(version="2026-11-19"))
    assert first.accepted_at is not None and again.accepted_at == first.accepted_at
    kept = await session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.action == own_proposals.TERMS_ACCEPTED, AuditLog.actorId == RESEARCHER)
    )
    assert kept == 1
    stored = await own_proposals.propose_on_site(session, researcher, body, now=NOW)
    assert (stored.outcome, stored.status) == ("STORED", "PENDING")


def _component_body() -> dict[str, Any]:
    return {
        "label": "open-work-test-craft/chemistry/zircovane-dye-docking",
        "title": "Zircovane dye docking",
        "description": "A turnable model of where the dye molecule docks on the zircovane crystal surface.",
        "kind": "molecule_3d",
        "field": "CHEMISTRY",
        "craftSlug": SLUG,
        "subjects": [{"kind": "CRAFT", "key": SLUG}],
        "consideredLabels": [WHAT_IF],
    }


async def test_a_fact_proposed_through_the_gates_is_listed_as_waiting_and_can_be_withdrawn(
    session: AsyncSession,
) -> None:
    researcher = await person(session, RESEARCHER)
    proposal = FactProposal.model_validate(
        {
            "subject": {"kind": "craft", "slug": SLUG},
            "field": "DESIGN",
            "statement": STATEMENT,
            "sources": [{"url": PAGE_URL, "title": "Indigo in Ajrakh", "quotes": [{"text": QUOTE}]}],
        }
    )
    gates = ProposalAdapters(
        fetcher=FakeFetcher({PAGE_URL: page()}), embed=FakeEmbedder(unit(1.0)), judge=FakeJudge()
    )
    reply = await propose_fact(session, proposal, researcher, "CONTRIBUTION", adapters=gates, now=NOW)
    assert reply.outcome == "WAITING"
    listed = {item.id: item for item in (await own_proposals.own_proposals(session, researcher)).items}
    mine = listed[reply.claim_id]
    assert (mine.state, mine.text, mine.craft_slug) == ("WAITING", STATEMENT, SLUG)
    assert [(gate.gate, gate.passed) for gate in mine.gates] == [
        (gate.gate, gate.passed) for gate in reply.gates
    ]
    assert (await own_proposals.withdraw_fact(session, researcher, reply.claim_id)).state == "WITHDRAWN"
