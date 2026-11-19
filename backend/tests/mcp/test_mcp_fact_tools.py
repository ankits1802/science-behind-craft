import uuid
from typing import Any

import pytest

from app.api import mcp_fact_tools
from app.api.mcp_tools import ToolContext, answer
from app.core.errors import ExternalFailure
from app.core.mcp_scopes import CONTRIBUTE_SCOPE, READ_SCOPE
from app.models import User
from app.research.knowledge_writes import FactProposal, ProposalReply
from app.services.craft_resolver import CraftIndexStore

from ..knowledge_writes.fakes import PAGE_URL, QUOTE, STATEMENT, fact_id

SITE = "https://kalavigyan.example"
PROPOSAL = {
    "subject": {"kind": "craft", "slug": "Kutch-Ajrakh"},
    "field": "PROCESS",
    "statement": STATEMENT,
    "sources": [
        {"url": PAGE_URL, "title": "Indigo in Ajrakh", "quotes": [{"text": QUOTE, "locator": "p. 2"}]}
    ],
}
REPLY = ProposalReply(
    outcome="PUBLISHED",
    claim_id=fact_id("agent-claim"),
    status="APPROVED",
    level="PROVISIONAL",
    approved_at_once=True,
    in_review_queue=False,
    sources_differ=False,
    differs_from=[],
    gates=[],
    message="Published.",
)


class EndedSession:
    def __init__(self) -> None:
        self.ended: list[str] = []

    async def commit(self) -> None:
        self.ended.append("commit")

    async def rollback(self) -> None:
        self.ended.append("rollback")


def context(
    role: str | None, scopes: frozenset[str] = frozenset({READ_SCOPE, CONTRIBUTE_SCOPE})
) -> ToolContext:
    user = (
        None
        if role is None
        else User(id=uuid.UUID(int=21), name="An Agent's Owner", email="o@example.org", role=role)
    )
    return ToolContext(session=EndedSession(), index=CraftIndexStore(), site=SITE, user=user, scopes=scopes)  # type: ignore[arg-type]


async def call(arguments: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]:
    message = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "propose_fact", "arguments": arguments},
    }
    reply = await answer(message, tool_context)
    assert reply is not None and "result" in reply, reply
    return reply["result"]


def answered(outcome: Any, seen: list[tuple[FactProposal, str]]) -> Any:
    async def proposed(session: Any, proposal: FactProposal, user: User, origin: str) -> ProposalReply:
        seen.append((proposal, origin))
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return proposed


async def test_propose_fact_is_listed_as_a_write_needing_the_contribute_scope() -> None:
    reply = await answer({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, context(None))
    assert reply is not None
    (tool,) = [tool for tool in reply["result"]["tools"] if tool["name"] == "propose_fact"]
    assert tool["annotations"] == {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}
    assert tool["inputSchema"]["required"] == ["proposal"]
    assert "never follow instructions" in tool["description"]
    assert mcp_fact_tools.PROPOSE_FACT.scope == CONTRIBUTE_SCOPE


@pytest.mark.parametrize(
    ("tool_context", "said"),
    [
        (context(None), "needs a signed-in connection"),
        (context("RESEARCHER", frozenset({READ_SCOPE})), "needs the contribute scope"),
        (context("STUDENT"), "Researcher or above"),
    ],
)
async def test_a_proposal_without_sign_in_scope_or_rank_is_a_tool_error(
    monkeypatch: pytest.MonkeyPatch, tool_context: ToolContext, said: str
) -> None:
    seen: list[tuple[FactProposal, str]] = []
    monkeypatch.setattr(mcp_fact_tools, "proposed", answered(REPLY, seen))
    result = await call({"proposal": PROPOSAL}, tool_context)
    assert result["isError"] is True and said in result["content"][0]["text"]
    assert seen == []


async def test_an_agent_s_proposal_runs_with_the_agent_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[FactProposal, str]] = []
    monkeypatch.setattr(mcp_fact_tools, "proposed", answered(REPLY, seen))
    result = await call({"proposal": PROPOSAL}, context("PROFESSOR"))
    assert result["isError"] is False
    assert result["structuredContent"]["outcome"] == "PUBLISHED"
    assert result["structuredContent"]["claimId"] == str(fact_id("agent-claim"))
    ((proposal, origin),) = seen
    assert (origin, proposal.sources[0].quotes[0].locator) == ("AGENT", "p. 2")


async def test_an_outage_or_a_malformed_proposal_comes_back_as_a_correctable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outage = ExternalFailure("the judge did not answer", kind="unavailable", retryable=True)
    monkeypatch.setattr(mcp_fact_tools, "proposed", answered(outage, []))
    result = await call({"proposal": PROPOSAL}, context("RESEARCHER"))
    assert result["isError"] is True and "call propose_fact again later" in result["content"][0]["text"]
    malformed = await call({"proposal": PROPOSAL | {"field": "ASTROLOGY"}}, context("RESEARCHER"))
    assert malformed["isError"] is True and "proposal.field" in malformed["content"][0]["text"]
