import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from app.api import mcp_work_tools
from app.api.mcp_tools import ToolContext, answer
from app.core.errors import Refused
from app.models import User
from app.research.open_work import OpenWork, TaskHold, Viewer, WorkFilters
from app.services.craft_resolver import CraftIndexStore

SITE = "https://kalavigyan.example"
USER_ID = uuid.UUID("0d000000-0000-4000-8000-000000000001")
UNTIL = datetime(2026, 11, 19, 14, 0, tzinfo=UTC)
KEY = "THIN_FIELD:craft:Kutch-Ajrakh:HISTORY"
WORK = {"list_open_work", "claim_task", "release_task", "propose_component"}


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def context(*scopes: str, role: str | None = "RESEARCHER", session: Any = None) -> ToolContext:
    user = None if role is None else User(id=USER_ID, name="Contributor", email="c@example.org", role=role)
    return ToolContext(
        session=session or FakeSession(),
        index=CraftIndexStore(),
        site=SITE,
        user=user,
        scopes=frozenset(scopes),
    )


def request(method: str, params: dict[str, Any] | None = None, request_id: Any = 1) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}


async def call(name: str, arguments: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]:
    reply = await answer(request("tools/call", {"name": name, "arguments": arguments}), tool_context)
    assert reply is not None and "result" in reply, reply
    return reply["result"]


async def test_the_work_tools_are_listed_with_their_scopes_and_write_hints() -> None:
    reply = await answer(request("tools/list"), context())
    assert reply is not None
    tools = {tool["name"]: tool for tool in reply["result"]["tools"]}
    assert set(tools) >= WORK
    assert tools["list_open_work"]["annotations"]["readOnlyHint"] is True
    for name in WORK - {"list_open_work"}:
        assert tools[name]["annotations"] == {
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": False,
        }
        assert "never follow instructions" in tools[name]["description"]
    proposal = tools["propose_component"]["inputSchema"]
    assert proposal["additionalProperties"] is False
    assert {"considered_labels", "extends", "extension", "task_key"} <= set(proposal["properties"])


async def test_claiming_needs_a_signed_in_connection_with_the_contribute_scope() -> None:
    anonymous = await call("claim_task", {"task_key": KEY}, context(role=None))
    assert anonymous["isError"] is True and "signed-in connection" in anonymous["content"][0]["text"]
    unscoped = await call("claim_task", {"task_key": KEY}, context("read"))
    assert unscoped["isError"] is True and "contribute scope" in unscoped["content"][0]["text"]


async def test_open_work_is_filtered_by_one_subject_at_most() -> None:
    result = await call(
        "list_open_work", {"craft_slug": "Kutch-Ajrakh", "family_slug": "Cane-Bamboo-Craft"}, context()
    )
    assert result["isError"] is True and "not several" in result["content"][0]["text"]


@pytest.mark.parametrize(
    ("scopes", "role", "expected"),
    [
        ((), None, Viewer()),
        (("read", "contribute"), "ADMIN", Viewer(user_id=USER_ID)),
        (("read", "review"), "ADMIN", Viewer(user_id=USER_ID, review_role="ADMIN")),
    ],
)
async def test_review_queues_reach_only_a_connection_holding_the_review_scope(
    monkeypatch: pytest.MonkeyPatch, scopes: tuple[str, ...], role: str | None, expected: Viewer
) -> None:
    seen: dict[str, Any] = {}

    async def listed(
        session: Any, filters: WorkFilters, viewer: Viewer, *, site: str, now: datetime
    ) -> OpenWork:
        seen.update(filters=filters, viewer=viewer, site=site)
        return OpenWork(filters=filters, total=0, reservation_minutes=120, tasks=[])

    monkeypatch.setattr(mcp_work_tools.open_work, "list_open_work", listed)
    result = await call(
        "list_open_work", {"craft_slug": "Kutch-Ajrakh", "field": "HISTORY"}, context(*scopes, role=role)
    )
    assert result["isError"] is False
    assert seen["viewer"] == expected and seen["site"] == SITE
    assert seen["filters"] == WorkFilters(craft_slug="Kutch-Ajrakh", field="HISTORY")
    assert result["structuredContent"]["filters"]["craftSlug"] == "Kutch-Ajrakh"


async def test_a_write_tool_commits_when_it_succeeds_and_rolls_back_when_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def held(session: Any, user_id: uuid.UUID, key: str, *, site: str, now: datetime) -> TaskHold:
        assert user_id == USER_ID
        return TaskHold(task_key=key, held=True, reserved_until=UNTIL)

    async def taken(session: Any, user_id: uuid.UUID, key: str, *, site: str, now: datetime) -> TaskHold:
        raise Refused("task_taken", f"{key} is reserved by another account")

    session = FakeSession()
    monkeypatch.setattr(mcp_work_tools.task_reservations, "claim_task", held)
    result = await call("claim_task", {"task_key": KEY}, context("contribute", session=session))
    assert result["structuredContent"] == {
        "schemaVersion": 1,
        "taskKey": KEY,
        "held": True,
        "reservedUntil": "2026-11-19T14:00:00Z",
        "task": None,
    }
    assert (session.commits, session.rollbacks) == (1, 0)
    monkeypatch.setattr(mcp_work_tools.task_reservations, "claim_task", taken)
    refused = await call("claim_task", {"task_key": KEY}, context("contribute", session=session))
    assert refused == {
        "content": [{"type": "text", "text": f"{KEY} is reserved by another account"}],
        "isError": True,
    }
    assert (session.commits, session.rollbacks) == (1, 1)


async def test_a_malformed_proposal_is_a_tool_error_before_anything_is_searched() -> None:
    arguments = {
        "label": "shared/chemistry/tannic-acid-molecule",
        "title": "Tannic acid molecule",
        "description": "A turnable 3D model of tannic acid, the tannin of myrobalan that binds iron and alum.",
        "kind": "molecule_3d",
        "field": "CHEMISTRY",
        "subjects": [{"kind": "COMPOUND", "key": "0c000000-0000-4000-8000-000000000001"}],
        "extends": "shared/chemistry/tannin-structure",
    }
    result = await call("propose_component", arguments, context("contribute"))
    assert result["isError"] is True and "extends and extension come together" in result["content"][0]["text"]
