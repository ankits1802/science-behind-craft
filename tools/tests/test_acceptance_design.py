from __future__ import annotations

from decimal import Decimal

from acceptance.loop import MODEL_STOPPED, LoopOutcome
from acceptance.opinion import OPINION_ASK, READ_HEAD, UNREAD_LINE, opinion_params
from acceptance.preview import (
    READ_PICTURES,
    Picture,
    critique_notes,
    design_notes,
    preview_facts,
    redraw_arguments,
)
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


def test_the_pictures_are_drawn_again_with_the_server_s_read_asked_for() -> None:
    given = {"draft_id": "d1", "critique": {"verdict": "Fine.", "notes": []}}
    assert redraw_arguments(given) == {**given, READ_PICTURES: True}
    assert READ_PICTURES not in given


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
    assert "The server's read of the pictures drawn again: 1 note." in summary
    assert summary.count(f"- {LINE}") == 2
    bare = summary_markdown(
        Evidence(facts=FACTS, outcome=LoopOutcome(MODEL_STOPPED, "end_turn", []), calls=[], spent=Decimal(0))
    )
    assert "Design notes" not in bare
