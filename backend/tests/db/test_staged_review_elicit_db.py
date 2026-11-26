import uuid
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mcp_tools import ToolContext
from app.models import AuditLog, StagedReview, User
from app.research.page_revalidation import PageOwners
from app.services import staged_review_finish
from app.services.craft_resolver import CraftIndexStore
from app.services.staged_review_views import open_batches

from ..mcp.modern_client import FORMS, modern, result_of, tool_call
from .review_queue_seed import ADMIN_OWN, AGENT_WAITING, LIVE, SLUG, People, seeded_session
from .test_staged_reviews_db import caller_of, statuses

pytestmark = pytest.mark.db

SITE = "https://kalavigyan.example"
WHY = "Both quotes say this of the vat, word for word."
NOTE = "Refreshing the pages these decisions touched now."
STAGE = {
    "decisions": [
        {"kind": "FACTS", "id": str(AGENT_WAITING), "action": "approve", "reason": WHY},
        {"kind": "FACTS", "id": str(LIVE), "action": "reject", "reason": WHY},
        {"kind": "FACTS", "id": str(ADMIN_OWN), "action": "approve", "reason": WHY},
    ]
}
ALL = {"confirm": {"action": "accept", "content": {"choice": "all"}}}


class Shelf:
    def start(self, work: Any, *, name: str) -> None:
        work.close()


@pytest.fixture
async def seeded() -> AsyncIterator[tuple[AsyncSession, People]]:
    async for opened in seeded_session():
        yield opened


@pytest.fixture
def refreshed(monkeypatch: pytest.MonkeyPatch) -> list[PageOwners]:
    seen: list[PageOwners] = []

    async def refresh(
        session: Any, owners: PageOwners, actor: User, background: Any, *, now: datetime
    ) -> str:
        seen.append(owners)
        return NOTE

    monkeypatch.setattr(staged_review_finish, "refresh_named", refresh)
    return seen


async def tools_of(
    session: AsyncSession, user: User, scopes: Sequence[str] = ("read", "review")
) -> ToolContext:
    caller = await caller_of(session, user)
    return ToolContext(
        session=session,
        index=CraftIndexStore(),
        site=SITE,
        user=user,
        scopes=frozenset(scopes),
        caller=caller,
        background=Shelf(),
    )


def staging(*, capabilities: dict[str, Any] = FORMS, **extra: Any) -> dict[str, Any]:
    return modern("tools/call", tool_call("stage_reviews", STAGE, **extra), capabilities=capabilities)


async def asked(tools: ToolContext) -> dict[str, Any]:
    first = await result_of(staging(), tools)
    assert first["resultType"] == "input_required", first
    return first


async def answered(tools: ToolContext, first: dict[str, Any], responses: dict[str, Any]) -> dict[str, Any]:
    reply = await result_of(staging(inputResponses=responses, requestState=first["requestState"]), tools)
    assert reply["isError"] is False, reply
    return reply["structuredContent"]


async def batch_of(session: AsyncSession, content: dict[str, Any]) -> StagedReview:
    batch = await session.get(StagedReview, uuid.UUID(content["batchId"]), populate_existing=True)
    assert batch is not None
    return batch


async def states_listed(session: AsyncSession, batch_id: uuid.UUID) -> list[str] | None:
    listed = await open_batches(session, now=datetime.now(UTC))
    found = [batch for batch in listed.batches if batch.id == batch_id]
    return [item.state for item in found[0].items] if found else None


async def test_a_batch_staged_over_mcp_and_confirmed_in_the_person_s_form_is_applied(
    seeded: tuple[AsyncSession, People], refreshed: list[PageOwners]
) -> None:
    session, people = seeded
    tools = await tools_of(session, people.admin)
    first = await asked(tools)
    message = first["inputRequests"]["confirm"]["params"]["message"]
    assert "\n1. Approve “An indigo vat turns blue at its surface.”: it is published for readers." in message
    assert "\n2. Reject “Lime keeps the indigo vat alkaline.”: it is not published" in message
    assert "\n3. " not in message and f"The reason given: “{WHY}”" in message
    assert await statuses(session) == {AGENT_WAITING: "DRAFT", LIVE: "IN_REVIEW"}
    content = await answered(tools, first, ALL)
    assert await statuses(session) == {AGENT_WAITING: "APPROVED", LIVE: "REJECTED"}
    assert content["published"] is True and [line["index"] for line in content["refused"]] == [2]
    assert [item["state"] for item in content["batch"]["items"]] == ["APPLIED", "APPLIED"]
    batch = await batch_of(session, content)
    assert (batch.status, batch.decidedById) == ("CONFIRMED", people.admin.id)
    applied = await session.scalars(select(AuditLog).where(AuditLog.action == "review.staged_applied"))
    assert {(row.actorId, (row.detail or {}).get("client")) for row in applied.all()} == {
        (people.admin.id, "Claude")
    }
    assert len(refreshed) == 1 and SLUG in refreshed[0].crafts and content["batch"]["refresh"] == NOTE


async def test_a_declined_form_leaves_the_batch_waiting_on_the_review_page(
    seeded: tuple[AsyncSession, People], refreshed: list[PageOwners]
) -> None:
    session, people = seeded
    tools = await tools_of(session, people.admin)
    content = await answered(tools, await asked(tools), {"confirm": {"action": "decline"}})
    assert "waits until an Admin confirms it" in content["message"] and "batch" not in content
    assert await statuses(session) == {AGENT_WAITING: "DRAFT", LIVE: "IN_REVIEW"}
    batch = await batch_of(session, content)
    assert batch.status == "OPEN" and await states_listed(session, batch.id) == ["STAGED", "STAGED"]
    assert refreshed == []


async def test_a_partial_confirmation_applies_only_the_ticked_item(
    seeded: tuple[AsyncSession, People], refreshed: list[PageOwners]
) -> None:
    session, people = seeded
    tools = await tools_of(session, people.admin)
    ticked = {"choice": "some", "item_1": False, "item_2": True}
    content = await answered(tools, await asked(tools), {"confirm": {"action": "accept", "content": ticked}})
    assert await statuses(session) == {AGENT_WAITING: "DRAFT", LIVE: "REJECTED"}
    assert [item["state"] for item in content["batch"]["items"]] == ["SKIPPED", "APPLIED"]
    assert (await batch_of(session, content)).status == "CONFIRMED"


async def test_a_client_without_elicitation_stages_and_waits_as_before(
    seeded: tuple[AsyncSession, People], refreshed: list[PageOwners]
) -> None:
    session, people = seeded
    reply = await result_of(staging(capabilities={}), await tools_of(session, people.admin))
    assert reply["resultType"] == "complete" and "inputRequests" not in reply
    content = reply["structuredContent"]
    assert content["message"].startswith("Nothing is published yet. 2 decisions wait in a staged batch")
    batch = await batch_of(session, content)
    assert await states_listed(session, batch.id) == ["STAGED", "STAGED"]
    assert await statuses(session) == {AGENT_WAITING: "DRAFT", LIVE: "IN_REVIEW"}


async def test_a_connection_without_the_review_scope_never_stages_or_gets_the_form(
    seeded: tuple[AsyncSession, People], refreshed: list[PageOwners]
) -> None:
    session, people = seeded
    tools = await tools_of(session, people.admin, ("read", "contribute"))
    reply = await result_of(staging(), tools)
    assert (
        reply["isError"] is True
        and "inputRequests" not in reply
        and "review scope" in reply["content"][0]["text"]
    )
    counted = await session.scalar(
        select(func.count(StagedReview.id)).where(StagedReview.proposerId == people.admin.id)
    )
    assert counted == 0
