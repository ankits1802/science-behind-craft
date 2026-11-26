from __future__ import annotations

import base64
import json
from decimal import Decimal
from typing import Any

from acceptance_support import PRICES, call, message, result, text, usage

from acceptance.connection import McpRefused
from acceptance.handed import HandedCall, client_tool, run_handed, stripped_texts
from acceptance.loop import MODEL_STOPPED, LoopOutcome, Turn
from acceptance.preview import READ_PICTURES, PreviewFacts
from acceptance.progress import build_progress, progress_lines
from acceptance.request import HARNESS_ADDS
from acceptance.spend import Carried, carried_cost, run_spend
from acceptance.transcript import Call, RunFacts, all_calls, transcript

JPEG = b"\xff\xd8a picture of the first screen"
PAYLOAD = base64.b64encode(JPEG).decode("ascii")
REPLY = {"previewUrl": "https://kalavigyan.example/preview/abc", "components": 3}
DRAWN = [
    {"type": "text", "text": json.dumps(REPLY)},
    {"type": "text", "text": "390 px, the first screen"},
    {"type": "image", "mimeType": "image/jpeg", "data": PAYLOAD},
]
FACTS = RunFacts(
    craft="Sanganeri-Hand-Block-Printing", request="Deepen it.", model="claude-opus-5-5", cap_usd="25"
)
USE = {"type": "tool_use", "id": "t1", "name": "preview_page", "input": {"draft_id": "d1"}}


def called(answer: dict[str, Any]):
    asked: list[tuple[str, dict[str, Any]]] = []

    def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        asked.append((name, arguments))
        return answer

    return call_tool, asked


def test_pictures_reach_the_model_as_one_line_and_never_as_their_payload() -> None:
    assert stripped_texts(DRAWN) == (
        json.dumps(REPLY),
        "390 px, the first screen",
        "1 pictures of this preview were kept by the run as files and not sent to you; the report above "
        "names each one and its drawing checks.",
    )
    assert stripped_texts(DRAWN[:2]) == (json.dumps(REPLY), "390 px, the first screen")


def test_the_run_calls_its_own_tool_keeps_the_pictures_and_hands_back_text_only() -> None:
    call_tool, asked = called({"content": DRAWN, "structuredContent": REPLY, "isError": False})
    handed = run_handed(call_tool, (McpRefused,), HARNESS_ADDS, 3, USE)
    assert asked == [("preview_page", {"draft_id": "d1", READ_PICTURES: True})]
    assert USE["input"] == {"draft_id": "d1"} and handed.arguments == asked[0][1]
    assert (handed.turn, handed.call_id, handed.is_error, handed.structured) == (3, "t1", False, REPLY)
    assert [(picture.name, picture.data) for picture in handed.pictures] == [
        ("01-390-px-the-first-screen.jpg", JPEG)
    ]
    block = handed.block()
    assert (block["type"], block["tool_use_id"], block["is_error"]) == ("tool_result", "t1", False)
    assert {item["type"] for item in block["content"]} == {"text"}
    assert PAYLOAD not in json.dumps(block)
    assert handed.chars == sum(len(item["text"]) for item in block["content"])


def test_a_tool_the_run_adds_nothing_to_is_called_as_the_model_asked() -> None:
    call_tool, asked = called({"content": DRAWN, "structuredContent": REPLY, "isError": False})
    run_handed(call_tool, (McpRefused,), {}, 3, USE)
    assert asked == [("preview_page", {"draft_id": "d1"})]


def test_a_refused_or_failed_call_is_handed_back_as_an_error_with_its_message() -> None:
    call_tool, _ = called({"content": [{"type": "text", "text": "Nothing was changed."}], "isError": True})
    refused = run_handed(call_tool, (McpRefused,), HARNESS_ADDS, 1, USE)
    assert (refused.texts, refused.is_error, refused.pictures) == (("Nothing was changed.",), True, ())

    def failing(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        raise McpRefused("tools/call answered HTTP 502")

    failed = run_handed(failing, (McpRefused,), HARNESS_ADDS, 1, USE)
    assert failed.is_error and failed.texts == (
        "The run could not call preview_page: McpRefused: tools/call answered HTTP 502",
    )


def test_a_listed_tool_becomes_a_client_tool_with_the_server_s_own_words() -> None:
    listed = {
        "name": "preview_page",
        "title": "Preview",
        "description": "Draw it.",
        "inputSchema": {"type": "object"},
    }
    assert client_tool(listed) == {
        "name": "preview_page",
        "description": "Draw it.",
        "input_schema": {"type": "object"},
        "eager_input_streaming": True,
    }


def run_of_two_turns() -> LoopOutcome:
    first = message(
        "pause_turn",
        [
            call("c1", "get_page", {"a": 1}),
            result("c1", ["x" * 300]),
            text("next"),
            call("c2", "get_facts"),
            result("c2", ["y" * 600]),
        ],
        usage(1_000, 2_000),
    )
    second = message("end_turn", [text("done")])
    turns = [
        Turn(1, first.model_dump(mode="json"), Decimal("0.044")),
        Turn(2, second.model_dump(mode="json"), Decimal(0)),
    ]
    return LoopOutcome(MODEL_STOPPED, "end_turn", turns)


def test_each_tool_is_charged_its_tokens_written_once_and_read_by_every_later_request() -> None:
    spent = run_spend(run_of_two_turns(), PRICES)
    assert spent.requests == 3
    assert (spent.input_usd, spent.output_usd) == (Decimal("0.004"), Decimal("0.04"))
    facts, page = spent.tools
    assert (facts.name, facts.calls, facts.result_chars, facts.argument_chars, facts.tokens) == (
        "get_facts",
        1,
        600,
        2,
        241,
    )
    assert facts.usd == Decimal("0.001225")
    assert (page.name, page.result_chars, page.argument_chars, page.tokens, page.usd) == (
        "get_page",
        300,
        8,
        124,
        Decimal("0.0007496"),
    )
    assert carried_cost(Carried("get_page", 300, 3), 3, PRICES) == 0


def test_the_run_s_own_calls_join_the_transcript_and_the_call_list() -> None:
    turn = Turn(1, message("tool_use", [text("previewing"), USE]).model_dump(mode="json"), Decimal(0))
    handed = HandedCall(1, "t1", "preview_page", {"draft_id": "d1"}, ("drawn",), False, chars=5)
    outcome = LoopOutcome(MODEL_STOPPED, "end_turn", [turn], [handed])
    (found,) = all_calls(outcome)
    assert (found.name, found.texts, found.answered, found.by_run, found.chars) == (
        "preview_page",
        ("drawn",),
        True,
        True,
        5,
    )
    blocks = transcript(FACTS, outcome)["turns"][0]["blocks"]
    assert [(block["type"], block.get("by")) for block in blocks] == [
        ("text", None),
        ("call", "run"),
        ("result", "run"),
    ]
    assert blocks[2]["pictures"] == [] and blocks[2]["text"] == "drawn"


def done(name: str, arguments: dict[str, Any], *, turn: int = 1, is_error: bool = False) -> Call:
    return Call(turn, f"c-{name}-{turn}", name, arguments, ("ok",), (), is_error, True)


def test_the_progress_says_how_far_the_build_got_and_what_it_never_reached() -> None:
    calls = [
        done("get_page", {"subject": {}, "parts": ["brief"]}),
        done("edit_draft", {"add": {"components": [{}, {}], "facts": [{}, {}, {}]}}, turn=2),
        done("edit_draft", {"add": {"components": [{}]}}, turn=3, is_error=True),
        done("edit_draft", {"add": {"layout": {"entries": []}}}, turn=3),
        done("preview_page", {"draft_id": "d1"}, turn=4),
    ]
    preview = PreviewFacts(None, 2, {}, {"passed": 20, "failed": 2}, (), None, (), (), ())
    assert progress_lines(build_progress(calls, preview)) == [
        "- Read the page's brief: 1 calls.",
        "- Opened a draft: in turn 2.",
        "- Added to the draft: 2 components and 3 facts in 2 edits.",
        "- Laid the page out: yes.",
        "- Previewed: 1 times, the last failing 2 rules.",
    ]
    assert progress_lines(build_progress(calls[:1], None)) == [
        "- Read the page's brief: 1 calls.",
        "- Opened a draft: not reached.",
        "- Added to the draft: not reached.",
        "- Laid the page out: not reached.",
        "- Previewed: not reached.",
    ]
