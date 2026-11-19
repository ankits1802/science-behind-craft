import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import knowledge_writes
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.errors import ExternalFailure, InvalidInput, Refused
from app.main import create_app
from app.models import User
from app.research.knowledge_writes import FactProposal, ProposalReply
from app.research.review_switch import ReviewSwitch, ReviewSwitchUpdate

from .fakes import PAGE_URL, QUOTE, STATEMENT, fact_id

PROPOSAL = {
    "subject": {"kind": "craft", "slug": "Kutch-Ajrakh"},
    "field": "PROCESS",
    "statement": STATEMENT,
    "sources": [{"url": PAGE_URL, "title": "Indigo in Ajrakh", "quotes": [{"text": QUOTE}]}],
}
REPLY = ProposalReply(
    outcome="WAITING",
    claim_id=fact_id("claim"),
    status="DRAFT",
    level="PROVISIONAL",
    approved_at_once=False,
    in_review_queue=True,
    sources_differ=False,
    differs_from=[],
    gates=[],
    message="Received.",
)


class Committed:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def client(role: str, session: Committed | None = None) -> TestClient:
    app = create_app()
    user = User(id=uuid.UUID(int=11), name="Asha Iyer", email="asha@example.org", role=role)
    app.dependency_overrides[get_current_user] = lambda: user

    async def opened() -> AsyncIterator[Any]:
        yield session or Committed()

    app.dependency_overrides[get_session] = opened
    return TestClient(app)


def answered(outcome: Any, seen: list[tuple[FactProposal, str]]) -> Any:
    async def proposed(session: Any, proposal: FactProposal, user: User, origin: str) -> ProposalReply:
        seen.append((proposal, origin))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return proposed


@pytest.fixture(autouse=True)
def terms_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    async def accepted(session: Any, user: User) -> None:
        return None

    monkeypatch.setattr(knowledge_writes, "require_terms", accepted)


def test_a_proposal_before_the_contribution_terms_are_accepted_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def not_accepted(session: Any, user: User) -> None:
        raise Refused("terms", "Accept the contribution terms, version 2026-11-19, before proposing.")

    seen: list[tuple[FactProposal, str]] = []
    monkeypatch.setattr(knowledge_writes, "require_terms", not_accepted)
    monkeypatch.setattr(knowledge_writes, "proposed", answered(REPLY, seen))
    response = client("RESEARCHER").post("/api/knowledge/facts", json=PROPOSAL)
    assert response.status_code == 403 and "contribution terms" in response.json()["detail"]
    assert seen == []


def test_a_student_may_not_propose_a_fact() -> None:
    assert client("STUDENT").post("/api/knowledge/facts", json=PROPOSAL).status_code == 403


def test_a_researcher_s_proposal_runs_as_a_site_contribution(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[FactProposal, str]] = []
    monkeypatch.setattr(knowledge_writes, "proposed", answered(REPLY, seen))
    response = client("RESEARCHER").post("/api/knowledge/facts", json=PROPOSAL)
    assert response.status_code == 200
    body = response.json()
    assert (body["outcome"], body["claimId"], body["inReviewQueue"]) == (
        "WAITING",
        str(fact_id("claim")),
        True,
    )
    ((proposal, origin),) = seen
    assert (origin, proposal.subject.slug) == ("CONTRIBUTION", "Kutch-Ajrakh")


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (InvalidInput("No craft has the slug 'Nowhere'"), 422),
        (Refused("no_account", "The account behind this proposal no longer exists."), 403),
        (ExternalFailure("the fetcher could not be reached", kind="unavailable", retryable=True), 503),
    ],
)
def test_a_refused_subject_account_or_an_outage_answers_with_its_status(
    monkeypatch: pytest.MonkeyPatch, error: Exception, status: int
) -> None:
    monkeypatch.setattr(knowledge_writes, "proposed", answered(error, []))
    assert client("PROFESSOR").post("/api/knowledge/facts", json=PROPOSAL).status_code == status


def test_a_malformed_proposal_is_refused_before_the_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[FactProposal, str]] = []
    monkeypatch.setattr(knowledge_writes, "proposed", answered(REPLY, seen))
    response = client("RESEARCHER").post("/api/knowledge/facts", json=PROPOSAL | {"sources": []})
    assert (response.status_code, seen) == (422, [])


def test_only_an_admin_reads_the_review_switch_with_its_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    async def current(session: Any) -> ReviewSwitch:
        return ReviewSwitch(agent="AUTO")

    monkeypatch.setattr(knowledge_writes.app_settings, "review_switch", current)
    assert client("PROFESSOR").get("/api/knowledge/review-switch").status_code == 403
    body = client("ADMIN").get("/api/knowledge/review-switch").json()
    assert body == {
        "current": {"research": "AUTO", "contribution": "APPROVAL", "agent": "AUTO"},
        "defaults": {"research": "AUTO", "contribution": "APPROVAL", "agent": "APPROVAL"},
    }


def test_an_admin_sets_one_origin_and_the_change_is_audited(monkeypatch: pytest.MonkeyPatch) -> None:
    changes: list[tuple[ReviewSwitchUpdate, Any]] = []
    audited: list[dict[str, Any]] = []

    async def set_switch(session: Any, update: ReviewSwitchUpdate, updated_by_id: Any) -> ReviewSwitch:
        changes.append((update, updated_by_id))
        return update.applied_to(ReviewSwitch())

    async def record(session: Any, **entry: Any) -> None:
        audited.append(entry)

    monkeypatch.setattr(knowledge_writes.app_settings, "set_review_switch", set_switch)
    monkeypatch.setattr(knowledge_writes.audit, "record", record)
    session = Committed()
    response = client("MASTER_ADMIN", session).put(
        "/api/knowledge/review-switch", json={"contribution": "AUTO"}
    )
    assert response.status_code == 200
    assert response.json()["current"] == {"research": "AUTO", "contribution": "AUTO", "agent": "APPROVAL"}
    ((update, by),) = changes
    assert (update.contribution, update.agent, by) == ("AUTO", None, uuid.UUID(int=11))
    assert audited[0]["detail"] == {
        "switch": {"RESEARCH": "AUTO", "CONTRIBUTION": "AUTO", "AGENT": "APPROVAL"}
    }
    assert session.commits == 1
    assert client("ADMIN").put("/api/knowledge/review-switch", json={"agent": "SOMETIMES"}).status_code == 422
