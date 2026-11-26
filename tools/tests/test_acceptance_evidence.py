from __future__ import annotations

import base64
import json
from decimal import Decimal

import pytest
from acceptance_support import PRICES, REPO, call, message, result, text

from acceptance.loop import MODEL_STOPPED, LoopOutcome, Turn
from acceptance.opinion import DESIGN_SKILL, OPINION_ASK, design_principles, opinion_params
from acceptance.pictures import Picture, reply_pictures
from acceptance.preview import last_preview, preview_facts, preview_reply
from acceptance.spend import run_spend
from acceptance.summary import Evidence, summary_markdown
from acceptance.transcript import RunFacts, block_entry, paired_calls, transcript, trimmed

FACTS = RunFacts(
    craft="Sanganeri-Hand-Block-Printing",
    request="Deepen this craft's page to the KalaVigyan bar.",
    model="claude-opus-5-5",
    cap_usd="12",
)
PREVIEW_URL = "https://kalavigyan.example/preview/abc"
REPLY = {
    "previewUrl": PREVIEW_URL,
    "components": 7,
    "report": {
        "passed": 20,
        "failed": 2,
        "judged": 6,
        "rules": [
            {"rule": 4, "title": "Every sentence is cited", "verdict": "PASS", "evidence": []},
            {"rule": 5, "title": "A stage player for every stage", "verdict": "FAIL", "evidence": []},
            {"rule": 27, "title": "Every theme draws", "verdict": "JUDGE", "evidence": []},
            {"rule": 28, "title": "The page draws whole at both widths", "verdict": "FAIL", "evidence": []},
        ],
        "figureKinds": {"reaction_player": 1, "map_layer": 2, "timeline": 1},
        "drawing": {
            "state": "FAILED",
            "problems": [{"width": 390, "label": "Chemistry, figure 2", "problem": "runs past its column"}],
            "images": [{"name": "phone-first-screen", "caption": "390 px, the first screen"}],
        },
        "bar": {
            "page": {"pictures": 2, "figures": 5, "interactives": 1, "maps": 1},
            "bar": {"pictures": 9, "figures": 71, "interactives": 14, "maps": 8},
        },
    },
}


def turns_with_a_preview() -> list[Turn]:
    first = message(
        "pause_turn",
        [
            call("c1", "edit_draft", {"craft": "Sanganeri-Hand-Block-Printing"}),
            result("c1", ["draft held"]),
            call("c2", "preview_page", {"draft_id": "d1"}),
            result("c2", ["not json"], is_error=True),
        ],
    )
    second = message(
        "end_turn",
        [call("c3", "preview_page", {"draft_id": "d1"}), result("c3", [json.dumps(REPLY)]), text("Done.")],
    )
    return [
        Turn(1, first.model_dump(mode="json"), Decimal("0.6")),
        Turn(2, second.model_dump(mode="json"), Decimal("0.63")),
    ]


def test_a_long_argument_or_result_is_trimmed_and_says_how_much_was_left_out() -> None:
    assert trimmed("a" * 4_500) == "a" * 4_000 + " [... 500 more characters]"
    assert trimmed("short") == "short"
    entry = block_entry(call("c1", "edit_draft", {"text": "b" * 5_000}))
    assert (entry["name"], entry["by"], entry["chars"]) == ("edit_draft", "connector", 5_012)
    assert entry["arguments"].endswith(" [... 1012 more characters]")
    assert len(entry["arguments"]) < 4_100
    kept = block_entry(call("c2", "edit_draft", {"text": "b" * 3_000}))
    assert kept["arguments"] == '{"text": "' + "b" * 3_000 + '"}'


def test_a_result_keeps_its_text_and_names_what_was_not_text() -> None:
    block = {
        "type": "mcp_tool_result",
        "tool_use_id": "c1",
        "is_error": False,
        "content": [{"type": "text", "text": "one"}, {"type": "image"}, {"type": "text", "text": "two"}],
    }
    assert block_entry(block) == {
        "type": "result",
        "callId": "c1",
        "isError": False,
        "text": "one\ntwo",
        "chars": 7,
        "otherContent": ["image"],
    }
    listing = {"type": "mcp_tool_listing", "mcp_server_name": "kalavigyan", "tools": [{"name": "get_page"}]}
    assert block_entry(listing) == {"type": "listing", "server": "kalavigyan", "tools": ["get_page"]}


def test_calls_are_paired_with_their_results_across_the_run() -> None:
    calls = paired_calls(turns_with_a_preview())
    assert [(found.turn, found.name, found.is_error) for found in calls] == [
        (1, "edit_draft", False),
        (1, "preview_page", True),
        (2, "preview_page", False),
    ]
    assert calls[0].arguments == {"craft": "Sanganeri-Hand-Block-Printing"}
    unanswered = paired_calls(
        [Turn(1, message("end_turn", [call("c9", "get_page")]).model_dump(mode="json"), Decimal(0))]
    )
    assert unanswered[0].answered is False
    assert [(found.chars, found.argument_chars) for found in calls] == [
        (10, 42),
        (8, 18),
        (len(json.dumps(REPLY)), 18),
    ]


def test_the_transcript_records_each_turn_with_its_cost_and_blocks() -> None:
    written = transcript(FACTS, LoopOutcome(MODEL_STOPPED, "end_turn", turns_with_a_preview()))
    assert (written["schemaVersion"], written["stopped"], written["trimmedAt"]) == (2, MODEL_STOPPED, 4_000)
    assert [turn["costUsd"] for turn in written["turns"]] == ["0.6", "0.63"]
    assert [block["type"] for block in written["turns"][1]["blocks"]] == ["call", "result", "text"]


def test_the_last_answered_preview_gives_its_link_verdicts_kinds_pictures_and_the_bar() -> None:
    found = last_preview(paired_calls(turns_with_a_preview()))
    assert found is not None and found.turn == 2
    facts = preview_facts(preview_reply(found.texts) or {})
    assert facts.preview_url == PREVIEW_URL
    assert facts.components == 7
    assert facts.figure_kinds == {"reaction_player": 1, "map_layer": 2, "timeline": 1}
    assert facts.verdicts == {"passed": 20, "failed": 2, "judged": 6}
    assert facts.failed_rules == (
        "5. A stage player for every stage",
        "28. The page draws whole at both widths",
    )
    assert facts.drawing_problems == ("390 px, Chemistry, figure 2: runs past its column",)
    assert facts.picture_names == ("phone-first-screen",)
    assert facts.beside_bar == ("pictures 2 of 9", "figures 5 of 71", "interactives 1 of 14", "maps 1 of 8")
    assert preview_reply(["not json"]) is None
    assert preview_reply([]) is None


def test_a_preview_that_answered_an_error_never_hides_the_one_that_drew_before_it() -> None:
    drew = message("pause_turn", [call("c1", "preview_page"), result("c1", [json.dumps(REPLY)])])
    failed = message("end_turn", [call("c2", "preview_page"), result("c2", ["refused"], is_error=True)])
    turns = [
        Turn(1, drew.model_dump(mode="json"), Decimal(0)),
        Turn(2, failed.model_dump(mode="json"), Decimal(0)),
    ]
    found = last_preview(paired_calls(turns))
    assert found is not None and found.call_id == "c1"
    only_failed = [Turn(1, failed.model_dump(mode="json"), Decimal(0))]
    assert last_preview(paired_calls(only_failed)) is None


def test_a_preview_s_pictures_are_named_from_their_captions_in_order() -> None:
    jpeg, png = b"\xff\xd8jpeg", b"\x89PNGpng"
    content = [
        {"type": "text", "text": json.dumps(REPLY)},
        {"type": "text", "text": "390 px, the first screen"},
        {"type": "image", "mimeType": "image/jpeg", "data": base64.b64encode(jpeg).decode("ascii")},
        {"type": "text", "text": "1440 px, Chemistry: Two mordants, one bath"},
        {"type": "image", "mimeType": "image/png", "data": base64.b64encode(png).decode("ascii")},
    ]
    pictures = reply_pictures(content)
    assert [(found.name, found.mime, found.data) for found in pictures] == [
        ("01-390-px-the-first-screen.jpg", "image/jpeg", jpeg),
        ("02-1440-px-chemistry-two-mordants-one-bath.png", "image/png", png),
    ]
    with pytest.raises(ValueError, match="image/gif"):
        reply_pictures([{"type": "image", "mimeType": "image/gif", "data": ""}])


def test_the_summary_names_calls_components_verdicts_pictures_and_cost() -> None:
    turns = turns_with_a_preview()
    calls = paired_calls(turns)
    outcome = LoopOutcome(MODEL_STOPPED, "end_turn", turns)
    evidence = Evidence(
        facts=FACTS,
        outcome=outcome,
        calls=calls,
        spent=Decimal("1.234"),
        spend=run_spend(outcome, PRICES),
        preview=preview_facts(REPLY),
        pictures=[("pictures/01-390-px-the-first-screen.jpg", "390 px, the first screen")],
        opinion="Meets principle 1.",
        notes=["The pictures were drawn again."],
    )
    summary = summary_markdown(evidence)
    assert summary.startswith("## Agent acceptance: Sanganeri Hand Block Printing\n")
    assert "Stopped: the model stopped (end_turn) after 2 turns." in summary
    assert "Cost: $1.23 of $12." in summary
    assert (
        "| `preview_page` | 2 | 1 | " in summary and "| `edit_draft` | 1 | 0 | 0.0 | 21 | $0.00 |" in summary
    )
    assert "- Turn 1, `preview_page`: not json" in summary
    assert "- Opened a draft: in turn 1." in summary
    assert "- Previewed: 1 times, the last failing 2 rules." in summary
    assert "(4 in this run)" in summary
    assert "| `map_layer` | 2 |" in summary
    assert "20 rules pass, 2 fail, 6 are left to judge on the private link." in summary
    assert "- Fails rule 28. The page draws whole at both widths" in summary
    assert (
        "Beside Kutch Ajrakh: pictures 2 of 9, figures 5 of 71, interactives 1 of 14, maps 1 of 8." in summary
    )
    assert f"Private link: {PREVIEW_URL}" in summary
    assert "- `pictures/01-390-px-the-first-screen.jpg`: 390 px, the first screen" in summary
    assert "(never the verdict)\n\nMeets principle 1." in summary


def test_a_run_without_a_preview_says_nothing_was_drawn() -> None:
    evidence = Evidence(
        facts=FACTS, outcome=LoopOutcome(MODEL_STOPPED, "end_turn", []), calls=[], spent=Decimal(0)
    )
    summary = summary_markdown(evidence)
    assert "The model called no tool." in summary
    assert "No preview_page call succeeded, so no page was drawn or checked." in summary
    assert "No picture was kept." in summary
    assert "second opinion" not in summary


def test_the_second_opinion_reads_the_design_skill_s_principles_and_non_negotiables_only() -> None:
    sample = "# Skill\n\n## 1. Principles\n\nOne.\n\n## 2. Non-negotiables\n\nTwo.\n\n## 3. Colour tokens\n\nThree."
    assert design_principles(sample) == "## 1. Principles\n\nOne.\n\n## 2. Non-negotiables\n\nTwo."
    real = design_principles((REPO / DESIGN_SKILL).read_text(encoding="utf-8"))
    assert real.startswith("## 1. Principles")
    assert "## 2. Non-negotiables" in real
    assert "## 3. " not in real
    with pytest.raises(ValueError, match="Principles"):
        design_principles("# A skill without them")


def test_the_second_opinion_is_shown_every_picture_with_its_caption_then_asked() -> None:
    picture = Picture("01-first.jpg", "390 px, the first screen", "image/jpeg", b"\xff\xd8")
    params = opinion_params("claude-opus-5-5", "## 1. Principles", [picture])
    content = params["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "## 1. Principles"}
    assert content[1] == {"type": "text", "text": "390 px, the first screen"}
    assert content[2]["source"] == {"type": "base64", "media_type": "image/jpeg", "data": "/9g="}
    assert content[-1] == {"type": "text", "text": OPINION_ASK}
    with pytest.raises(ValueError, match="picture"):
        opinion_params("claude-opus-5-5", "## 1. Principles", [])
