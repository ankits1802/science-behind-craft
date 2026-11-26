import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.api import mcp_report_reads
from app.api.mcp_gap_tools import NEXT_STEP
from app.api.mcp_report_pages import ReportAsk
from app.api.mcp_tools import ToolContext, answer
from app.core.mcp_scopes import CONTRIBUTE_SCOPE, READ_SCOPE, REVIEW_SCOPE
from app.core.rate_limit import SITE_GAPS, SITE_GAPS_PER_WINDOW
from app.models import AuditLog, User
from app.research.site_gaps import SITE_GAP_ACTION, SITE_GAP_TARGET, SiteGap
from app.services.craft_resolver import CraftIndexStore
from app.services.site_gaps import gap_detail, gap_row

from ..allowance_counter import MemoryCounter

NOW = datetime(2026, 11, 26, 9, tzinfo=UTC)
GAP = {
    "subject": {"kind": "craft", "slug": "Sanganeri-Hand-Block-Printing"},
    "kind": "KIND",
    "wanted": "A stage player whose scenes move the cloth through each of the thirteen stages.",
    "tried": "compose_component for a stage_player",
    "evidence": [
        "compose_component composes dip_player, reaction_player, experiment_lab and choice_toggle only"
    ],
}


class Recording:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0

    def add(self, row: Any) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


def person(role: str) -> User:
    return User(id=uuid.uuid4(), name=f"{role} person", email=f"{role.lower()}@example.org", role=role)


def context(user: User, session: Any, *scopes: str) -> ToolContext:
    held = frozenset(scopes or (READ_SCOPE, CONTRIBUTE_SCOPE))
    return ToolContext(
        session=session, index=CraftIndexStore(), site="https://k.example", user=user, scopes=held
    )


async def reported(arguments: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]:
    params = {"name": "report_site_gap", "arguments": arguments}
    reply = await answer({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": params}, tool_context)
    assert reply is not None and "result" in reply, reply
    return reply["result"]


async def test_a_contributor_s_agent_files_a_gap_with_its_evidence_where_the_admins_read_it() -> None:
    session = Recording()
    result = await reported(GAP, context(person("RESEARCHER"), session))
    assert result["isError"] is False
    filed = result["structuredContent"]
    assert filed["filed"] is True and filed["kind"] == "KIND" and filed["nextStep"] == NEXT_STEP
    (row,) = session.added
    assert isinstance(row, AuditLog) and row.action == SITE_GAP_ACTION
    assert (row.targetType, row.targetId) == (SITE_GAP_TARGET, "craft:Sanganeri-Hand-Block-Printing")
    assert row.detail == {
        "kind": "KIND",
        "subject": "craft:Sanganeri-Hand-Block-Printing",
        "wanted": GAP["wanted"],
        "tried": GAP["tried"],
        "evidence": GAP["evidence"],
        "client": None,
    }


@pytest.mark.parametrize(
    "changes",
    [{"evidence": []}, {"wanted": "A player"}, {"kind": "WISH"}, {"evidence": ["one"] * 6}],
)
async def test_a_gap_without_evidence_or_with_no_kind_the_site_knows_is_refused(
    changes: dict[str, Any],
) -> None:
    session = Recording()
    result = await reported({**GAP, **changes}, context(person("RESEARCHER"), session))
    assert result["isError"] is True and session.added == []


async def test_a_reader_s_connection_cannot_file_a_gap() -> None:
    session = Recording()
    result = await reported(GAP, context(person("STUDENT"), session))
    assert result["isError"] is True and session.added == []


async def test_a_spent_gap_allowance_refuses_the_next(allowance_counter: MemoryCounter) -> None:
    researcher, session = person("RESEARCHER"), Recording()
    allowance_counter.fill(str(researcher.id), SITE_GAPS, SITE_GAPS_PER_WINDOW)
    result = await reported(GAP, context(researcher, session))
    assert (
        result["isError"] is True
        and f"{SITE_GAPS_PER_WINDOW} site gap reports" in result["content"][0]["text"]
    )
    assert session.added == []


def test_a_filed_gap_reads_back_whole_and_names_no_account() -> None:
    detail = gap_detail(SiteGap.model_validate(GAP), "Claude")
    row = gap_row(NOW, detail).model_dump(mode="json", by_alias=True)
    assert row == {
        "filedAt": "2026-11-26T09:00:00Z",
        "kind": "KIND",
        "subject": "craft:Sanganeri-Hand-Block-Printing",
        "wanted": GAP["wanted"],
        "tried": GAP["tried"],
        "evidence": GAP["evidence"],
        "client": "Claude",
    }


async def test_the_admins_read_the_gaps_newest_first_in_their_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filed = [gap_row(NOW, gap_detail(SiteGap.model_validate(GAP), None))]
    asked: list[int] = []

    async def recent(session: Any, *, days: int, now: datetime) -> list[Any]:
        asked.append(days)
        return filed

    monkeypatch.setattr(mcp_report_reads, "recent_gaps", recent)
    admin = context(person("ADMIN"), Recording(), READ_SCOPE, REVIEW_SCOPE)
    page = await mcp_report_reads.READERS["site_gaps"](admin, ReportAsk(now=NOW, days=7))
    assert asked == [7] and page.total == 1 and page.items[0]["kind"] == "KIND"
    assert "the last 7 days" in page.message
    params = {"name": "admin_reports", "arguments": {"report": "site_gaps"}}
    refused = await answer(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": params},
        context(person("RESEARCHER"), Recording(), READ_SCOPE, REVIEW_SCOPE),
    )
    assert refused is not None and refused["result"]["isError"] is True
