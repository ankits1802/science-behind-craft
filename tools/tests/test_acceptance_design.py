from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from acceptance_support import FakeClient, message, run_call, text

from acceptance import run
from acceptance.loop import MODEL_STOPPED, LoopOutcome
from acceptance.opinion import OPINION_ASK, READ_HEAD, UNREAD_LINE, opinion_params
from acceptance.pictures import Picture
from acceptance.preview import READ_PICTURES, critique_notes, design_notes, preview_facts
from acceptance.summary import Evidence, summary_markdown
from acceptance.transcript import RunFacts

FACTS = RunFacts(
    craft="Sanganeri-Hand-Block-Printing",
    request="Deepen this craft's page to the KalaVigyan bar.",
    model="claude-opus-5-5",
    cap_usd="12",
)
NOTE = {
    "chapter": "made",
    "where": "the eight paragraphs on washing",
    "problem": "A wall of text with no figure beside it.",
    "fix": "Step through the washes with a stage player.",
}
LINE = "made, the eight paragraphs on washing: A wall of text with no figure beside it. Step through the washes with a stage player."
PICTURE = Picture("01-first.jpg", "390 px, the first screen", "image/jpeg", b"\xff\xd8")


def reply(read: dict | None = None, critique: dict | None = None) -> dict:
    return {
        "previewUrl": "https://kalavigyan.example/preview/abc",
        "report": {"designRead": read, "critique": critique},
    }


@dataclass
class PreviewServer:
    drawn: dict[str, Any]
    asked: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    server: str = "https://api.example/api/mcp"

    def __call__(self, path: Path, http: Any, *, mask: Any) -> PreviewServer:
        return self

    def token(self) -> str:
        return "kvmcp_at_fixture-not-a-token"

    def instructions(self) -> str:
        return "Start with the brief."

    def listed_tools(self) -> list[dict[str, Any]]:
        return [{"name": "preview_page", "description": "Draw it.", "inputSchema": {"type": "object"}}]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.asked.append((name, arguments))
        content = [
            {"type": "text", "text": json.dumps(self.drawn)},
            {"type": "text", "text": PICTURE.caption},
            {
                "type": "image",
                "mimeType": PICTURE.mime,
                "data": base64.b64encode(PICTURE.data).decode("ascii"),
            },
        ]
        return {"content": content, "structuredContent": self.drawn, "isError": False}


def handed_run(monkeypatch: pytest.MonkeyPatch, out: Path, server: PreviewServer) -> FakeClient:
    client = FakeClient(
        [
            message("tool_use", [run_call("t1", "preview_page", {"draft_id": "d1"})]),
            message("end_turn", [text("Done.")]),
            message("end_turn", [text("A fair page, 6 out of 10.")]),
        ]
    )
    monkeypatch.setattr(run, "McpConnection", server)
    monkeypatch.setattr(run.anthropic, "Anthropic", lambda **_: client)
    asked = ["run", "--craft", FACTS.craft, "--request", FACTS.request, "--cap", "12", "--model", FACTS.model]
    assert run.main([*asked, "--token-file", str(out / "token.json"), "--out", str(out)]) == 0
    return client


@pytest.mark.parametrize(
    ("read", "weighed", "counted"),
    [
        ({"state": "READ", "notes": [NOTE]}, f"{READ_HEAD}\n- {LINE}", "1 note"),
        ({"state": "SKIPPED", "notes": [], "reason": "The drawing failed."}, UNREAD_LINE, "no notes"),
    ],
)
def test_a_handed_preview_asks_for_the_server_s_read_and_its_notes_reach_the_second_opinion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, read: dict[str, Any], weighed: str, counted: str
) -> None:
    server = PreviewServer(reply(read))
    client = handed_run(monkeypatch, tmp_path, server)
    assert server.asked == [("preview_page", {"draft_id": "d1", READ_PICTURES: True})]
    handed_back = client.requests[1]["messages"][-1]["content"][0]["content"]
    assert {item["type"] for item in handed_back} == {"text"}
    opinion = client.requests[2]["messages"][0]["content"]
    assert [item["type"] for item in opinion].count("image") == 1
    assert opinion[-2:] == [{"type": "text", "text": weighed}, {"type": "text", "text": OPINION_ASK}]
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert f"The server's read of the last preview's pictures: {counted}." in summary
    assert "with read_pictures added" in summary and "drawn again" not in summary


def test_only_a_read_that_ran_gives_notes_to_the_second_opinion() -> None:
    assert design_notes(reply({"state": "READ", "notes": [NOTE]})) == (LINE,)
    assert design_notes(reply({"state": "SKIPPED", "notes": [], "reason": "The drawing failed."})) == ()
    assert design_notes(reply()) == () and design_notes({}) == ()


def test_the_model_s_own_critique_is_read_from_its_last_preview() -> None:
    assert critique_notes(reply(critique={"verdict": "A wall.", "notes": [NOTE]})) == (LINE,)
    assert critique_notes(reply()) == ()


def test_the_second_opinion_weighs_the_server_s_notes_before_it_is_asked() -> None:
    content = opinion_params("claude-opus-5-5", "## 1. Principles", [PICTURE], read=[LINE])["messages"][0][
        "content"
    ]
    assert content[-2] == {"type": "text", "text": f"{READ_HEAD}\n- {LINE}"}
    assert content[-1] == {"type": "text", "text": OPINION_ASK}
    unread = opinion_params("claude-opus-5-5", "## 1. Principles", [PICTURE])["messages"][0]["content"]
    assert unread[-2] == {"type": "text", "text": UNREAD_LINE}


def test_the_summary_lists_the_model_s_critique_and_the_server_s_read_as_notes_never_the_verdict() -> None:
    preview = preview_facts(reply(critique={"verdict": "A wall.", "notes": [NOTE]}))
    evidence = Evidence(
        facts=FACTS,
        outcome=LoopOutcome(MODEL_STOPPED, "end_turn", []),
        calls=[],
        spent=Decimal(1),
        preview=preview,
        read=[LINE],
    )
    summary = summary_markdown(evidence)
    assert "### Design notes (never the verdict)" in summary
    assert "The model's own critique with its last preview: 1 note." in summary
    assert "The server's read of the last preview's pictures: 1 note." in summary
    assert summary.count(f"- {LINE}") == 2
    bare = summary_markdown(
        Evidence(facts=FACTS, outcome=LoopOutcome(MODEL_STOPPED, "end_turn", []), calls=[], spent=Decimal(0))
    )
    assert "Design notes" not in bare
