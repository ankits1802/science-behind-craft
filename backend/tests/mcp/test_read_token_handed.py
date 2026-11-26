import uuid
from datetime import datetime
from typing import Any

import pytest

from app.api import mcp_page_tools
from app.api.mcp_guide_steps import design_read_token, design_sheets
from app.models import PageDraft, User
from app.research.page_proposals import PageSubject

from ..research.test_page_proposals import COMPONENT, FACT
from .test_mcp_page_read import call as read_page
from .test_mcp_studio_tools import DRAFT_ID, FakeSession, call, context, draft_row, owned

SUBJECT = {"kind": "craft", "slug": "Kutch-Ajrakh"}
DELIVERED = {"proposal": COMPONENT}


def design_addresses() -> list[str]:
    return [sheet.address for sheet in design_sheets()]


def opened(monkeypatch: pytest.MonkeyPatch, row: PageDraft) -> list[Any]:
    added: list[Any] = []

    async def created(session: Any, user: User, subject: PageSubject, *, now: datetime) -> PageDraft:
        return row

    async def add(
        session: Any, user: User, draft_id: uuid.UUID, addition: Any, *, now: datetime
    ) -> PageDraft:
        added.append(addition)
        return row

    monkeypatch.setattr(mcp_page_tools.page_drafts, "create_draft", created)
    monkeypatch.setattr(mcp_page_tools.page_drafts, "own_draft", owned(row))
    monkeypatch.setattr(mcp_page_tools.page_drafts, "add_to_draft", add)
    return added


async def test_opening_a_draft_hands_the_design_pages_and_their_token_so_no_call_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    added = opened(monkeypatch, draft_row({"facts": [FACT]}))
    first = await call(
        "edit_draft", {"subject": SUBJECT, "add": {"facts": [FACT]}}, context(session=FakeSession())
    )
    guide = first["structuredContent"]["guide"]
    assert first["isError"] is False
    assert [page["address"] for page in guide["pages"]] == design_addresses()
    assert guide["readToken"] == design_read_token()
    built = await call(
        "edit_draft",
        {"draft_id": str(DRAFT_ID), "add": {"components": [DELIVERED]}, "read_token": guide["readToken"]},
    )
    assert built["isError"] is False and len(added) == 2


async def test_a_later_edit_or_a_draft_that_holds_components_is_handed_no_design_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened(monkeypatch, draft_row({"facts": [FACT]}))
    later = await call("edit_draft", {"draft_id": str(DRAFT_ID), "add": {"facts": [FACT]}})
    assert later["isError"] is False and "guide" not in later["structuredContent"]
    opened(monkeypatch, draft_row({"facts": [FACT], "components": [DELIVERED]}))
    reopened = await call("edit_draft", {"subject": SUBJECT, "add": {"facts": [FACT]}})
    assert reopened["isError"] is False and "guide" not in reopened["structuredContent"]


async def test_reading_a_design_page_hands_both_and_the_token_and_another_page_hands_none() -> None:
    for address in design_addresses():
        guide = (await read_page({"guide": address}))["structuredContent"]["guide"]
        assert [page["address"] for page in guide["pages"]] == design_addresses()
        assert guide["readToken"] == design_read_token()
    other = (await read_page({"guide": "bar/1"}))["structuredContent"]["guide"]
    assert "readToken" not in other and [page["address"] for page in other["pages"]] == ["bar/1"]


async def test_components_sent_without_the_token_are_still_refused_with_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    added = opened(monkeypatch, draft_row({"facts": [FACT]}))
    refused = await call("edit_draft", {"draft_id": str(DRAFT_ID), "add": {"components": [DELIVERED]}})
    assert refused["isError"] is True and design_read_token() in refused["content"][0]["text"]
    assert added == []
