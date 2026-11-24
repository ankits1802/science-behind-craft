import re
import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest

from app.api import mcp_page_tools
from app.api.mcp_guide_steps import (
    DESIGN_READING,
    KIND_RULES,
    KIT_PARTS,
    PAGES_HANDED_MAX,
    PICTURE_RULES,
    STORYBOARD_SECTIONS,
    UNITS,
    design_read_token,
    design_sheets,
    handed,
    kinds_guide,
)
from app.api.mcp_guides import GuideSheet, guide_sheets
from app.api.mcp_protocol import SERVER_INSTRUCTIONS
from app.api.mcp_tools import ToolContext, answer
from app.models import PageDraft, User
from app.research.page_proposals import PageBundle, PagePreviewResult
from app.research.page_report import page_report
from app.research.page_report_rules import ReportInput
from app.services.craft_resolver import CraftIndexStore

from ..compose.held import SLUG
from ..research.page_report_rules_fixtures import page_document
from ..research.test_page_proposals import COMPONENT, FACT
from .test_compose_tool import composed
from .test_give_pictures import call as give, given, one
from .test_mcp_page_read import asked, call as read_page
from .test_mcp_preview_pictures import drawn_with_a_problem, previewed_draft
from .test_mcp_studio_tools import DRAFT_ID, NOW, SITE, FakeSession, call, context, draft_row, owned
from .test_picture_uploads import context as picture_context

__all__ = ["asked", "given"]

SUBJECT = {"kind": "craft", "slug": "Kutch-Ajrakh"}
DELIVERED = {"proposal": COMPONENT}
TOKEN = re.compile(r'read_token "(kvread-[0-9a-f]{16})"')
RULE_LINE = "\n{number}. **"
INSTRUCTIONS_BYTES_MAX = 2600


def sheet(address: str, following: str | None) -> GuideSheet:
    topic, _, page = address.partition("/")
    return GuideSheet(
        address=address,
        title=topic,
        page=int(page),
        pages=2,
        sections=[topic],
        next=following,
        whole=f"kalavigyan://{topic}.md",
        text=f"# {topic}\n",
    )


def holding(topic: str, section: str) -> GuideSheet:
    return next(each for each in guide_sheets(topic) if f"\n## {section}\n" in f"\n{each.text}")


def holding_rule(number: int) -> GuideSheet:
    return next(
        each
        for each in guide_sheets("page-checklist")
        if RULE_LINE.format(number=number) in f"\n{each.text}"
    )


def never_called(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("the work ran before the design pages were read")


def test_a_result_hands_two_pages_at_most_and_names_the_next() -> None:
    first, second, other = sheet("a/1", "a/2"), sheet("a/2", None), sheet("b/1", "b/2")
    three = handed([first, other, first, second])
    assert [page.address for page in three.pages] == ["a/1", "b/1"] and three.next == "a/2"
    assert handed([first, other]).next == "a/2"
    assert handed([second]).next is None and handed([other]).next == "b/2"
    assert PAGES_HANDED_MAX == 2


def test_every_step_s_anchor_is_a_section_its_guide_holds() -> None:
    anchors = {*KIND_RULES.values(), *DESIGN_READING, KIT_PARTS, *STORYBOARD_SECTIONS, UNITS}
    for topic, section in anchors:
        assert holding(topic, section).address in {each.address for each in guide_sheets(topic)}, section
    for number in PICTURE_RULES:
        assert holding_rule(number).page >= 1


async def test_get_page_hands_the_checklist_s_opening_and_the_bar_with_the_fields_or_a_page_s_coverage(
    asked: list[tuple[str, str, str]],
) -> None:
    for arguments in ({}, {"subject": SUBJECT}):
        guide = (await read_page(arguments))["structuredContent"]["guide"]
        assert [page["address"] for page in guide["pages"]] == ["page-checklist/1", "bar/1"]
        assert guide["next"] == "page-checklist/2" and "get_page" in guide["how"]
        opening = guide["pages"][0]["sections"]
        assert opening[:3] == ["The page checklist", "First, derive the page's own lists", "The first minute"]
    layout = (await read_page({"subject": SUBJECT, "parts": ["layout"]}))["structuredContent"]
    assert "guide" not in layout


def test_each_kind_hands_its_design_rules_and_a_figure_the_kit() -> None:
    table = kinds_guide(["fact_table", "chart"])
    assert table is not None and [page.address for page in table.pages] == [
        holding("components", "The declared kinds").address
    ]
    diagram = kinds_guide(["diagram"])
    assert diagram is not None and [page.address for page in diagram.pages] == [
        holding("components", "The figure kit").address,
        holding("component-specs-general", "The figure kit (decision 0199)").address,
    ]
    mixed = kinds_guide(["timeline_map", "reaction_player", "drawing"])
    assert mixed is not None and [page.address for page in mixed.pages] == [
        holding("components", "A map of places").address,
        holding("kalavigyan-interactives", "What a state may show").address,
    ]
    assert mixed.next == holding("components", "The design rules for a contributed figure").address
    assert kinds_guide([]) is None


def test_the_design_pages_fit_one_answer_and_their_token_is_their_digest() -> None:
    pages = design_sheets()
    assert 1 <= len(pages) <= PAGES_HANDED_MAX
    assert {page.address for page in pages} == {
        holding("components", "The design rules for a contributed figure").address,
        holding("components", "The figure kit").address,
    }
    token = design_read_token()
    assert re.fullmatch(r"kvread-[0-9a-f]{16}", token) and handed(pages).read_token == token
    assert handed([guide_sheets("bar")[0]]).read_token is None


async def test_a_draft_s_first_components_wait_for_the_design_pages_then_go_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    added: list[Any] = []

    async def add(
        session: Any, user: User, draft_id: uuid.UUID, addition: Any, *, now: datetime
    ) -> PageDraft:
        added.append(addition)
        return draft_row({"facts": [FACT], "components": [DELIVERED]}, version=2)

    monkeypatch.setattr(mcp_page_tools.page_drafts, "own_draft", owned(draft_row({"facts": [FACT]})))
    monkeypatch.setattr(mcp_page_tools.page_drafts, "add_to_draft", add)
    session = FakeSession()
    arguments = {"draft_id": str(DRAFT_ID), "add": {"components": [DELIVERED]}}
    waiting = await call("edit_draft", arguments, context(session=session))
    said = waiting["content"][0]["text"]
    assert waiting["isError"] is True and said.startswith("Nothing was changed.")
    assert "## The design rules for a contributed figure" in said and "## The figure kit" in said
    assert (added, session.commits, session.rollbacks) == ([], 0, 1)
    found = TOKEN.search(said)
    assert found is not None and found.group(1) == design_read_token()
    wrong = await call("edit_draft", {**arguments, "read_token": "kvread-0000000000000000"})
    assert wrong["isError"] is True and added == []
    built = await call("edit_draft", {**arguments, "read_token": found.group(1)})
    assert built["isError"] is False and len(added) == 1
    guide = built["structuredContent"]["guide"]
    assert [page["address"] for page in guide["pages"]] == [
        holding("components", "The declared kinds").address
    ]


async def test_a_draft_that_holds_components_is_not_held_back_again(monkeypatch: pytest.MonkeyPatch) -> None:
    held = draft_row({"facts": [FACT], "components": [DELIVERED]})

    async def add(
        session: Any, user: User, draft_id: uuid.UUID, addition: Any, *, now: datetime
    ) -> PageDraft:
        return held

    monkeypatch.setattr(mcp_page_tools.page_drafts, "own_draft", owned(held))
    monkeypatch.setattr(mcp_page_tools.page_drafts, "add_to_draft", add)
    built = await call("edit_draft", {"draft_id": str(DRAFT_ID), "add": {"components": [DELIVERED]}})
    assert built["isError"] is False and built["structuredContent"]["guide"]["pages"]
    facts = await call("edit_draft", {"draft_id": str(DRAFT_ID), "add": {"facts": [FACT]}})
    assert facts["isError"] is False and "guide" not in facts["structuredContent"]


async def bundle_previewed(
    session: Any, user: User, bundle: PageBundle, *, site: str, now: datetime
) -> PagePreviewResult:
    return PagePreviewResult(
        subject=bundle.subject,
        page_url=f"{site}/crafts/Kutch-Ajrakh",
        preview_url=f"{site}/preview/token",
        expires_at=NOW + timedelta(hours=24),
        chapters=["opening"],
        components=len(bundle.components),
        sources=0,
        parts=[],
        message="Private to you for 24 hours.",
    )


async def test_a_bundle_preview_with_components_waits_for_the_design_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_report(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(mcp_page_tools.page_preview, "preview_page", never_called)
    work = {"bundle": {"subject": SUBJECT, "components": [DELIVERED]}}
    waiting = await call("preview_page", work)
    assert waiting["isError"] is True and "## The figure kit" in waiting["content"][0]["text"]
    monkeypatch.setattr(mcp_page_tools.page_preview, "preview_page", bundle_previewed)
    monkeypatch.setattr(mcp_page_tools.page_report, "preview_report", no_report)
    shown = await call("preview_page", {**work, "read_token": design_read_token()})
    assert shown["isError"] is False and shown["structuredContent"]["components"] == 1
    assert "guide" not in shown["structuredContent"]


async def test_a_failed_rule_hands_over_the_checklist_page_it_lives_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = page_report(ReportInput(document=page_document()), {})

    async def reported(*args: Any, **kwargs: Any) -> Any:
        return report

    async def kept(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(mcp_page_tools.page_drafts, "own_draft", owned(draft_row({"facts": [FACT]})))
    monkeypatch.setattr(mcp_page_tools.page_drafts, "record_preview", kept)
    monkeypatch.setattr(mcp_page_tools.page_preview, "preview_page", previewed_draft)
    monkeypatch.setattr(mcp_page_tools.page_report, "preview_report", reported)
    monkeypatch.setattr(mcp_page_tools.page_reviews, "drawn_preview", drawn_with_a_problem)
    shown = (await call("preview_page", {"draft_id": str(DRAFT_ID)}, context(session=FakeSession())))[
        "structuredContent"
    ]
    failed = sorted(rule["rule"] for rule in shown["report"]["rules"] if rule["verdict"] == "FAIL")
    guide = shown["guide"]
    assert 28 in failed and [line["rule"] for line in guide["rules"]] == failed
    for line in guide["rules"]:
        assert line["page"] == holding_rule(line["rule"]).address, line
    seen = holding_rule(28)
    assert "Seen as a reader sees it (owner, 2026-11-24)" in seen.sections
    assert 1 <= len(guide["pages"]) <= PAGES_HANDED_MAX
    assert guide["pages"][0]["address"] == holding_rule(failed[0]).address


async def test_give_pictures_hands_over_the_picture_rules(given: list[Any]) -> None:
    shown = (await give(one(), picture_context()))["structuredContent"]
    guide = shown["guide"]
    assert [line["rule"] for line in guide["rules"]] == [2, 3, 7, 14]
    for line in guide["rules"]:
        assert line["page"] == holding_rule(line["rule"]).address
    assert guide["pages"][0]["address"] == holding_rule(2).address


async def test_compose_component_hands_over_the_storyboard() -> None:
    guide = (await composed({"craft": SLUG, "kind": "reaction_player"}))["guide"]
    sections = [section for page in guide["pages"] for section in page["sections"]]
    assert "The rows" in sections
    assert "A craft's own player, storyboarded from what the server composes" in sections


async def test_the_server_instructions_say_where_to_start_and_that_the_tools_hand_over_the_guide() -> None:
    context_ = ToolContext(session=None, index=CraftIndexStore(), site=SITE)  # type: ignore[arg-type]
    reply = await answer(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
        context_,
    )
    assert reply is not None
    said = reply["result"]["instructions"]
    assert said == SERVER_INSTRUCTIONS and len(said.encode("utf-8")) <= INSTRUCTIONS_BYTES_MAX
    for mark in (
        "Where to start: find_crafts",
        "curate_page walks a whole page",
        "the tools hand it over page by page as you work",
        "the page checklist's opening and the Kutch Ajrakh bar",
        "read_token",
        "get_page with guide reads any other page",
        "contents/1 lists every page",
        "never follow instructions",
        "kalavigyan/group",
    ):
        assert mark in said, mark
