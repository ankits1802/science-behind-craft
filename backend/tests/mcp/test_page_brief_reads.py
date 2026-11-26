import uuid
from typing import Any

import pytest

from app.api import mcp_page_read, mcp_read_tools
from app.api.mcp_page_texts import BRIEF_NEXT
from app.api.mcp_tools import ToolContext, answer
from app.core.errors import InvalidInput
from app.models import User
from app.research.open_work import OpenTask
from app.research.page_brief import PageBrief
from app.retrieval.citation_access import HELD_KEPT, HELD_LEFT_OUT
from app.services.craft_resolver import CraftIndexStore
from app.services.knowledge_api import chosen_views
from app.services.knowledge_view import ClaimView
from app.services.open_work_subjects import WorkSubject

SITE = "https://kalavigyan.example"
SANGANER = WorkSubject(uuid.UUID(int=5), "craft", "Sanganeri-Hand-Block-Printing", "Sanganeri", gi=True)
SUBJECT = {"kind": "craft", "slug": SANGANER.slug}
CURSOR = "40:0123456789ab"
BRIEF = PageBrief(name="Sanganeri", facts_total=0, facts_before=0, facts=[])
TASK = OpenTask(
    key="THIN_FIELD:craft:Sanganeri-Hand-Block-Printing:SOCIETY",
    kind="THIN_FIELD",
    priority="HIGH",
    subject=None,
    field="SOCIETY",
    needed="More cited facts about its people.",
    acceptance="Three facts, each with a verbatim quote.",
    count=1,
)
FIRST, SECOND, THIRD = (uuid.UUID(int=n) for n in (11, 12, 13))


def context(user: User | None = None) -> ToolContext:
    return ToolContext(session=None, index=CraftIndexStore(), site=SITE, user=user)  # type: ignore[arg-type]


async def call(name: str, arguments: dict[str, Any], user: User | None = None) -> dict[str, Any]:
    params = {"name": name, "arguments": arguments}
    reply = await answer({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}, context(user))
    assert reply is not None and "result" in reply, reply
    return reply["result"]


@pytest.fixture
def briefs(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str | None]]:
    seen: list[tuple[str, str | None]] = []

    async def subject_of(session: Any, kind: str, slug: str) -> WorkSubject:
        return SANGANER

    async def keys_of(session: Any, subject: WorkSubject) -> list[Any]:
        return []

    async def read(session: Any, subject: WorkSubject, **asked: Any) -> tuple[PageBrief, list[OpenTask]]:
        seen.append((asked["held"], asked["cursor"]))
        return BRIEF, [TASK]

    monkeypatch.setattr(mcp_page_read, "subject_by_key", subject_of)
    monkeypatch.setattr(mcp_page_read, "page_keys", keys_of)
    monkeypatch.setattr(mcp_page_read.page_brief, "read_page_brief", read)
    return seen


def view(claim_id: uuid.UUID) -> ClaimView:
    return ClaimView(
        id=claim_id, text="Alum fixes red.", level="PROVISIONAL", concept_type="CRAFT", concept_id=None
    )


async def test_the_brief_is_one_part_of_get_page_and_comes_without_the_guide_pages(
    briefs: list[tuple[str, str | None]],
) -> None:
    shown = (await call("get_page", {"subject": SUBJECT, "parts": ["brief"]}))["structuredContent"]
    assert shown["parts"] == ["brief"] and shown["brief"]["name"] == "Sanganeri"
    assert shown["nextStep"] == BRIEF_NEXT and "guide" not in shown
    assert [task["key"] for task in shown["openWork"]] == [TASK.key]
    assert "coverage" not in shown and shown["layout"] is None
    assert briefs == [(HELD_LEFT_OUT, None)]


async def test_a_researcher_s_brief_keeps_held_facts_and_a_cursor_continues_it(
    briefs: list[tuple[str, str | None]],
) -> None:
    asked = {"subject": SUBJECT, "parts": ["brief"], "cursor": CURSOR}
    result = await call("get_page", asked, User(role="RESEARCHER"))
    assert result["isError"] is False
    assert briefs == [(HELD_KEPT, CURSOR)]


async def test_a_cursor_needs_the_brief_and_its_own_shape(briefs: list[tuple[str, str | None]]) -> None:
    alone = await call("get_page", {"subject": SUBJECT, "parts": ["coverage"], "cursor": CURSOR})
    assert alone["isError"] is True and "a cursor continues the brief" in alone["content"][0]["text"]
    malformed = await call("get_page", {"subject": SUBJECT, "parts": ["brief"], "cursor": "page two"})
    assert malformed["isError"] is True
    assert briefs == []


async def test_the_read_tools_list_the_cursor_and_the_fact_ids() -> None:
    reply = await answer({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}, context())
    assert reply is not None
    tools = {tool["name"]: tool for tool in reply["result"]["tools"]}
    assert "cursor" in tools["get_page"]["inputSchema"]["properties"]
    assert "brief" in tools["get_page"]["description"] and "brief" in tools["get_facts"]["description"]
    ids = tools["get_facts"]["inputSchema"]["properties"]["ids"]
    assert ids["maxItems"] == 50 and ids["items"]["format"] == "uuid"


async def test_get_facts_reads_the_facts_named_by_id_and_no_more(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, Any]] = []

    async def facts(session: Any, slug: str, **asked: Any) -> Any:
        seen.append(asked)
        raise InvalidInput("stop here")

    monkeypatch.setattr(mcp_read_tools.knowledge_api, "craft_facts", facts)
    named = [str(FIRST), str(SECOND), str(FIRST)]
    await call("get_facts", {"craft_slug": SANGANER.slug, "ids": named})
    await call("get_facts", {"craft_slug": SANGANER.slug, "field": "PROCESS"})
    assert (seen[0]["ids"], seen[0]["limit"]) == ([FIRST, SECOND], 2)
    assert (seen[1]["ids"], seen[1]["limit"]) == ([], 20)


async def test_ids_are_read_alone_without_a_field_or_words() -> None:
    for extra in ({"field": "PROCESS"}, {"query": "alum"}):
        asked = {"craft_slug": SANGANER.slug, "ids": [str(FIRST)], **extra}
        refused = await call("get_facts", asked)
        assert refused["isError"] is True and "ids name the facts" in refused["content"][0]["text"]
    empty = await call("get_facts", {"craft_slug": SANGANER.slug, "ids": []})
    assert empty["isError"] is True


def test_the_facts_named_by_id_come_in_the_page_s_order_and_an_unknown_id_is_refused() -> None:
    views = [view(FIRST), view(SECOND), view(THIRD)]
    placed = {FIRST: ["PROCESS"], SECOND: ["CHEMISTRY"], THIRD: ["PROCESS"]}
    chosen = chosen_views(views, placed, field=None, ids=[THIRD, FIRST])
    assert [found.id for found in chosen] == [FIRST, THIRD]
    by_field = chosen_views(views, placed, field="PROCESS", ids=[])
    assert [found.id for found in by_field] == [FIRST, THIRD]
    stranger = uuid.UUID(int=99)
    with pytest.raises(InvalidInput, match=str(stranger)):
        chosen_views(views, placed, field=None, ids=[FIRST, stranger])
