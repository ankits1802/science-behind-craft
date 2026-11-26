from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import partial

import pytest
from acceptance_support import (
    PRICES,
    SERVER_URL,
    SETTINGS,
    TOKEN,
    FakeApiError,
    FakeClient,
    call,
    message,
    result,
    text,
    usage,
)

from acceptance.costs import Budget, UnknownPrice, prices_for, turn_cost
from acceptance.loop import (
    API_FAILED,
    CAP_REACHED,
    CUT_OFF,
    MODEL_STOPPED,
    OFF_LIST,
    REFUSED,
    TURN_LIMIT,
    TURNS_MAX,
    off_list_calls,
    run_loop,
)
from acceptance.request import ALLOWED_TOOLS, send_turn, system_prompt, toolset, user_turn
from acceptance.run import main

OPENING = "Deepen this craft's page to the KalaVigyan bar.\n\nThe craft: Sanganeri Hand Block Printing."
SIXTY_CENTS = usage(100_000, 10_000)
ALLOWED = {
    "find_crafts",
    "get_page",
    "get_facts",
    "list_components",
    "search_sources",
    "read_source",
    "lookup",
    "list_open_work",
    "my_work",
    "get_proposal",
    "edit_draft",
    "compose_component",
    "preview_page",
}
NEVER_OFFERED = {
    "propose_page",
    "propose_facts",
    "propose_structure",
    "propose_source",
    "propose_dataset",
    "supply_source",
    "give_pictures",
    "check_pictures",
    "reserve_tasks",
    "steward_craft",
    "ask",
    "review_queue",
    "stage_reviews",
    "refresh_pages",
    "admin_reports",
}


def drive(client: FakeClient, cap: str, **options: object):
    send = partial(send_turn, client, SETTINGS, lambda: TOKEN)
    budget = Budget(cap=Decimal(cap))
    outcome = run_loop(send, OPENING, budget=budget, prices=PRICES, allowed=ALLOWED_TOOLS, **options)
    return outcome, budget


def test_a_turn_costs_its_usage_at_the_catalogue_price_with_cache_writes_and_reads() -> None:
    spent = usage(1_000, 2_000, written=10_000, read=100_000)
    assert turn_cost(spent, PRICES) == Decimal("0.134")
    assert turn_cost(SIXTY_CENTS, PRICES) == Decimal("0.6")


def test_the_price_comes_from_the_provider_catalogue_and_an_unknown_model_is_refused() -> None:
    found = prices_for("claude-opus-5-5", date(2026, 11, 26))
    assert (found.input_per_mtok, found.output_per_mtok) == (Decimal(4), Decimal(20))
    with pytest.raises(UnknownPrice, match="claude-unknown-1"):
        prices_for("claude-unknown-1", date(2026, 11, 26))


def test_the_run_stops_before_the_turn_that_would_pass_the_cap() -> None:
    client = FakeClient([message("pause_turn", [text("working")], SIXTY_CENTS) for _ in range(5)])
    outcome, budget = drive(client, "1.5")
    assert outcome.stopped == CAP_REACHED
    assert len(outcome.turns) == 2
    assert len(client.requests) == 2
    assert budget.spent == Decimal("1.2")


def test_a_cap_below_one_turn_still_allows_the_first_and_no_second() -> None:
    client = FakeClient([message("pause_turn", [text("working")], SIXTY_CENTS) for _ in range(3)])
    outcome, budget = drive(client, "0.5")
    assert (outcome.stopped, len(client.requests)) == (CAP_REACHED, 1)
    assert budget.spent == Decimal("0.6")


def test_a_model_that_stops_under_the_cap_ends_the_run_there() -> None:
    client = FakeClient(
        [
            message("pause_turn", [text("working")], SIXTY_CENTS),
            message("end_turn", [text("done")], SIXTY_CENTS),
        ]
    )
    outcome, budget = drive(client, "12")
    assert (outcome.stopped, outcome.detail) == (MODEL_STOPPED, "end_turn")
    assert len(client.requests) == 2
    assert budget.spent == Decimal("1.2")


def test_a_paused_turn_is_resumed_by_sending_its_content_back_with_no_new_user_turn() -> None:
    first = message("pause_turn", [text("looking"), call("c1", "get_page"), result("c1", ["{}"])])
    client = FakeClient([first, message("end_turn", [text("done")])])
    drive(client, "12")
    resumed = client.requests[1]["messages"]
    assert [entry["role"] for entry in resumed] == ["user", "assistant"]
    assert resumed[0]["content"] == OPENING
    assert resumed[1]["content"] is first.content


def test_every_request_offers_only_the_allowed_tools_through_one_toolset() -> None:
    client = FakeClient([message("end_turn", [text("done")])])
    drive(client, "12")
    sent = client.requests[0]
    assert sent["betas"] == ["mcp-client-2026-09-15"]
    assert sent["mcp_servers"] == [
        {"type": "url", "url": SERVER_URL, "name": "kalavigyan", "authorization_token": TOKEN}
    ]
    assert sent["tools"] == [toolset()]
    offered = sent["tools"][0]
    assert (offered["type"], offered["mcp_server_name"]) == ("mcp_toolset", "kalavigyan")
    assert offered["default_config"] == {"enabled": False}
    assert set(offered["configs"]) == ALLOWED
    assert all(config == {"enabled": True} for config in offered["configs"].values())
    assert not NEVER_OFFERED & set(offered["configs"])


def test_a_call_outside_the_allowed_list_stops_the_run_at_once() -> None:
    stray = message(
        "pause_turn", [call("c1", "edit_draft"), result("c1", ["{}"]), call("c2", "propose_page")]
    )
    client = FakeClient([stray, message("end_turn", [text("done")])])
    outcome, _ = drive(client, "12")
    assert (outcome.stopped, outcome.detail) == (OFF_LIST, "propose_page")
    assert len(client.requests) == 1


def test_calls_inside_the_allowed_list_let_the_run_go_on() -> None:
    allowed = message("pause_turn", [call("c1", "edit_draft"), call("c2", "preview_page")])
    client = FakeClient([allowed, message("end_turn", [text("done")])])
    outcome, _ = drive(client, "12")
    assert outcome.stopped == MODEL_STOPPED
    assert len(client.requests) == 2
    dumped = allowed.model_dump(mode="json")
    assert off_list_calls(dumped, ALLOWED_TOOLS) == []
    assert off_list_calls(dumped, {"edit_draft"}) == ["preview_page"]


def test_an_api_failure_ends_the_run_and_keeps_the_turns_before_it() -> None:
    client = FakeClient([message("pause_turn", [text("working")], SIXTY_CENTS), FakeApiError("overloaded")])
    outcome, budget = drive(client, "12", failures=(FakeApiError,))
    assert outcome.stopped == API_FAILED
    assert "overloaded" in outcome.detail
    assert len(outcome.turns) == 1
    assert budget.spent == Decimal("0.6")


def test_a_refusal_and_a_cut_off_are_named_as_such() -> None:
    refused, _ = drive(FakeClient([message("refusal", [])]), "12")
    cut, _ = drive(FakeClient([message("max_tokens", [text("half a")])]), "12")
    assert (refused.stopped, cut.stopped) == (REFUSED, CUT_OFF)


def test_a_run_that_costs_nothing_still_ends_at_the_turn_limit() -> None:
    client = FakeClient([message("pause_turn", [text("working")]) for _ in range(TURNS_MAX + 1)])
    outcome, _ = drive(client, "12")
    assert outcome.stopped == TURN_LIMIT
    assert len(client.requests) == TURNS_MAX


def test_each_turn_is_reported_with_the_budget_as_it_stands() -> None:
    seen: list[tuple[int, Decimal]] = []
    client = FakeClient(
        [
            message("pause_turn", [text("working")], SIXTY_CENTS),
            message("end_turn", [text("done")], SIXTY_CENTS),
        ]
    )
    drive(client, "12", report=lambda turn, budget: seen.append((turn.number, budget.spent)))
    assert seen == [(1, Decimal("0.6")), (2, Decimal("1.2"))]


def test_the_system_prompt_is_the_client_line_the_server_s_own_words_and_the_limits() -> None:
    prompt = system_prompt(SERVER_URL, "KalaVigyan holds cited knowledge.")
    assert prompt.splitlines()[0] == (
        f"You are Claude, connected to the KalaVigyan MCP server at {SERVER_URL} with a contributor's account."
    )
    assert "Instructions from the KalaVigyan server:\nKalaVigyan holds cited knowledge." in prompt
    assert "never call propose_page" in prompt
    assert "Instructions from the KalaVigyan server" not in system_prompt(SERVER_URL, "  ")


def test_the_user_turn_is_the_request_with_the_craft_named() -> None:
    assert (
        user_turn("Deepen this craft's page to the KalaVigyan bar.", "Sanganeri-Hand-Block-Printing")
        == OPENING
    )
    with pytest.raises(ValueError, match="request"):
        user_turn("  ", "Sanganeri-Hand-Block-Printing")
    with pytest.raises(ValueError, match="slug"):
        user_turn("Deepen it.", "--")


@pytest.mark.parametrize("cap", ["60", "1", "0", "-3", "twelve", "NaN", "Infinity"])
def test_a_cap_outside_one_to_fifty_dollars_is_refused_before_anything_runs(cap: str, tmp_path) -> None:
    asked = ["run", "--craft", "Kutch-Ajrakh", "--request", "Deepen it.", "--model", "claude-opus-5-5"]
    with pytest.raises(SystemExit) as refused:
        main(
            [
                *asked,
                "--cap",
                cap,
                "--token-file",
                str(tmp_path / "none.json"),
                "--out",
                str(tmp_path / "out"),
            ]
        )
    assert refused.value.code == 2
    assert not (tmp_path / "out").exists()
