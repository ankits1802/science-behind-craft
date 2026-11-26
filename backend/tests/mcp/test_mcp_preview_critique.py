import re
from decimal import Decimal
from typing import Any

import pytest

from app.api import mcp_page_tools
from app.api.mcp_page_texts import REVIEWED
from app.api.mcp_rule_fixes import FIXES_HEAD, RULE_FIXES, rule_fixes
from app.api.mcp_tools import TOOLS
from app.research.design_critique import DesignCritique, DesignNote
from app.research.design_read import READ, DesignRead
from app.research.page_report import page_report
from app.research.page_report_rules import ReportInput
from app.services.page_reviews import DrawnPreview

from ..research.page_report_rules_fixtures import page_document
from ..research.test_page_proposals import FACT
from .test_mcp_preview_pictures import SHOT, drawn_with_a_problem, previewed_draft
from .test_mcp_studio_tools import DRAFT_ID, FakeSession, call, context, draft_row, owned

CRITIQUE = {
    "verdict": "The making chapter is a wall of prose.",
    "notes": [
        {
            "chapter": "made",
            "where": "the eight paragraphs on washing",
            "problem": "A wall of text with no figure beside it.",
            "fix": "Step through the washes with a stage player.",
        }
    ],
}
NOTE = DesignNote(chapter="opening", where="the masthead", problem="No plate.", fix="Set the dye plate.")


def previewing(monkeypatch: pytest.MonkeyPatch, read: DesignRead | None = None) -> list[dict[str, Any]]:
    seen: list[dict[str, Any]] = []
    report = page_report(ReportInput(document=page_document()), {})

    async def reported(*args: Any, **kwargs: Any) -> Any:
        return report

    async def kept(*args: Any, **kwargs: Any) -> None:
        return None

    async def critiqued(session: Any, user: Any, previewed: Any, drawn: DrawnPreview, **kwargs: Any) -> Any:
        seen.append({"critique": kwargs["critique"]})
        given = kwargs["critique"]
        if given is None or drawn.report is None:
            return drawn
        return DrawnPreview(report=drawn.report.model_copy(update={"critique": given}), images=drawn.images)

    async def designed(session: Any, user: Any, drawn: DrawnPreview, **kwargs: Any) -> Any:
        seen.append({"asked": kwargs["asked"]})
        if not kwargs["asked"] or drawn.report is None:
            return drawn
        return DrawnPreview(report=drawn.report.model_copy(update={"design_read": read}), images=drawn.images)

    monkeypatch.setattr(mcp_page_tools.page_drafts, "own_draft", owned(draft_row({"facts": [FACT]})))
    monkeypatch.setattr(mcp_page_tools.page_drafts, "record_preview", kept)
    monkeypatch.setattr(mcp_page_tools.page_preview, "preview_page", previewed_draft)
    monkeypatch.setattr(mcp_page_tools.page_report, "preview_report", reported)
    monkeypatch.setattr(mcp_page_tools.page_reviews, "drawn_preview", drawn_with_a_problem)
    monkeypatch.setattr(mcp_page_tools.page_critique, "critiqued", critiqued)
    monkeypatch.setattr(mcp_page_tools.page_design_read, "designed_preview", designed)
    return seen


async def preview(arguments: dict[str, Any]) -> dict[str, Any]:
    shown = await call(
        "preview_page", {"draft_id": str(DRAFT_ID), **arguments}, context(session=FakeSession())
    )
    assert shown["isError"] is False, shown
    return shown


async def test_a_critique_given_with_a_preview_is_recorded_and_shown_and_none_is_asked_of_the_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = previewing(monkeypatch)
    shown = await preview({"critique": CRITIQUE})
    assert seen == [{"critique": DesignCritique.model_validate(CRITIQUE)}, {"asked": False}]
    report = shown["structuredContent"]["report"]
    assert report["critique"] == CRITIQUE and report["designRead"] is None
    failed = sorted(rule["rule"] for rule in report["rules"] if rule["verdict"] == "FAIL")
    fixes = "; ".join(f"rule {number}, {RULE_FIXES[number]}" for number in failed)
    assert failed and set(failed) <= set(RULE_FIXES)
    assert shown["structuredContent"]["nextStep"] == f"{REVIEWED}{FIXES_HEAD}{fixes}."
    assert "design-critique/1" in REVIEWED
    assert shown["content"][1:] == [
        {"type": "text", "text": SHOT.caption},
        {"type": "image", "data": SHOT.data, "mimeType": "image/jpeg"},
    ]


async def test_without_a_critique_or_read_pictures_the_preview_asks_the_agent_to_critique(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = previewing(monkeypatch)
    shown = await preview({})
    assert seen == [{"critique": None}, {"asked": False}]
    report = shown["structuredContent"]["report"]
    assert report["critique"] is None and report["designRead"] is None
    assert "read_pictures" in shown["structuredContent"]["nextStep"]


async def test_read_pictures_asks_the_server_and_its_notes_join_the_next_step_without_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read = DesignRead(
        state=READ, verdict="Needs a plate.", notes=[NOTE], chapters=["opening"], cost_usd=Decimal(0)
    )
    seen = previewing(monkeypatch, read)
    shown = await preview({"read_pictures": True})
    assert seen[-1] == {"asked": True}
    content = shown["structuredContent"]
    assert content["report"]["designRead"]["notes"][0]["where"] == "the masthead"
    assert content["nextStep"].startswith(REVIEWED)
    assert "opening, the masthead: No plate. Set the dye plate." in content["nextStep"]
    assert content["report"]["failed"] == page_report(ReportInput(document=page_document()), {}).failed + 1


async def test_a_critique_off_its_shape_is_refused_with_its_reason() -> None:
    shown = await call("preview_page", {"draft_id": str(DRAFT_ID), "critique": {"notes": []}})
    assert shown["isError"] is True and "verdict" in shown["content"][0]["text"]


def test_the_preview_s_input_names_the_critique_and_read_pictures_without_a_dangling_reference() -> None:
    schema = TOOLS["preview_page"].listed()["inputSchema"]
    properties = schema["properties"]
    assert (
        properties["critique"]["required"] == ["verdict"]
        and "design-critique/1" in properties["critique"]["description"]
    )
    assert properties["read_pictures"]["type"] == "boolean" and "$defs" not in schema
    assert "$ref" not in str(properties["critique"])


def test_each_rule_the_sanganeri_run_left_failing_names_the_tool_that_fixes_it() -> None:
    for number in (2, 6, 9, 15, 20, 23, 24, 25, 26, 28):
        assert set(re.findall(r"[a-z_]+", RULE_FIXES[number])) & set(TOOLS), number
    assert "give_pictures" in RULE_FIXES[2] and "MASTHEAD" in RULE_FIXES[2]
    assert "edit_draft add facts in that field" in RULE_FIXES[23]


def test_a_preview_with_no_failed_rule_or_only_judged_ones_names_no_fix() -> None:
    assert rule_fixes([]) == ""
    assert rule_fixes([5, 8, 11]) == ""
    assert rule_fixes([28, 2, 28]).startswith(f"{FIXES_HEAD}rule 2, give_pictures")
