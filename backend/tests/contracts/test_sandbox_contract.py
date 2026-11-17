import time
from typing import Any

import pytest

from app.research.sandbox import (
    FORBIDDEN_APIS,
    LAYOUT_CONSTANTS,
    SANDBOX_CSP,
    SANDBOX_MAX_BYTES,
    SANDBOX_RULES,
    sandbox_problems,
)

from .phase_c_golden import corpus, phase_c_blocks

PLAN_FORBIDDEN = (
    "fetch",
    "XMLHttpRequest",
    "WebSocket",
    "EventSource",
    "sendBeacon",
    "import",
    "eval",
    "Function",
    "Worker",
    "SharedWorker",
    "importScripts",
    "cookie",
    "localStorage",
    "sessionStorage",
    "indexedDB",
    "postMessage",
    "location",
)


def refused_cases() -> list[dict[str, Any]]:
    return corpus()["refused"]


def accepted_cases() -> list[dict[str, Any]]:
    return corpus()["accepted"]


def values() -> dict[str, float]:
    return corpus()["values"]


@pytest.mark.parametrize("case", refused_cases(), ids=lambda case: case["name"])
def test_each_escape_attempt_is_refused_by_its_own_rule(case: dict[str, Any]) -> None:
    assert {problem.rule for problem in sandbox_problems(case["html"], values())} == {case["rule"]}


@pytest.mark.parametrize("case", accepted_cases(), ids=lambda case: case["name"])
def test_ordinary_explainer_code_passes(case: dict[str, Any]) -> None:
    assert sandbox_problems(case["html"], values()) == []


def test_the_corpus_tries_every_rule_and_the_plan_s_forbidden_apis() -> None:
    assert {case["rule"] for case in refused_cases()} == set(SANDBOX_RULES) - {"SIZE"}
    assert len({case["name"] for case in refused_cases()}) == len(refused_cases())
    assert set(PLAN_FORBIDDEN) <= set(FORBIDDEN_APIS)
    tried = " ".join(case["html"] for case in refused_cases() if case["rule"] == "API")
    assert all(name in tried for name in PLAN_FORBIDDEN)


def test_the_generated_explainer_of_the_fixture_is_an_accepted_case() -> None:
    simulation = phase_c_blocks()["s1.b1"]
    assert accepted_cases()[0]["html"] == simulation["html"]
    assert values() == {value["key"]: value["value"] for value in simulation["values"]}


def test_the_size_cap_is_two_hundred_kibibytes_of_utf8() -> None:
    assert SANDBOX_MAX_BYTES == 204800
    filler = "<p>Water</p>"
    exact = filler * (SANDBOX_MAX_BYTES // len(filler)) + "x" * (SANDBOX_MAX_BYTES % len(filler))
    assert len(exact.encode("utf-8")) == SANDBOX_MAX_BYTES
    assert sandbox_problems(exact, {}) == []
    over = exact[:-1] + "é"
    assert [problem.rule for problem in sandbox_problems(over, {})] == ["SIZE"]


def test_a_data_value_may_be_shown_and_only_a_data_value() -> None:
    shown = "<p>About 450 years</p>"
    assert [p.rule for p in sandbox_problems(shown, {})] == ["NUMBER"]
    assert sandbox_problems(shown, {"yearsAtDhamadka": 450.0}) == []
    assert sandbox_problems("<p>Down 3 feet</p>", {"fall": -3.0}) == []


def test_layout_constants_hold_in_code_and_never_in_shown_text() -> None:
    assert {0.0, 1.0, 12.0, 100.0, 360.0, 1000.0, 0.5} <= LAYOUT_CONSTANTS
    assert {13.0, 50.0, 450.0} & LAYOUT_CONSTANTS == set()
    assert sandbox_problems("<script>const turn = 360;</script>", {}) == []
    assert [p.rule for p in sandbox_problems("<p>Turn 360 degrees</p>", {})] == ["NUMBER"]


def test_a_self_closed_script_or_style_is_still_read_as_the_browser_reads_it() -> None:
    script = "<p>Water</p><script/>fetch('#a');parent.postMessage(document.cookie, '*');</script>"
    assert {problem.rule for problem in sandbox_problems(script, {})} == {"MARKUP", "API"}
    style = "<style/>p{background:url(https://example.org/a.png)}</style>"
    assert {problem.rule for problem in sandbox_problems(style, {})} == {"MARKUP", "URL"}


def test_the_frame_policy_blocks_peer_connections_where_a_browser_reads_the_directive() -> None:
    assert SANDBOX_CSP.endswith("; webrtc 'block'")


@pytest.mark.parametrize(
    "html",
    [
        "<style>" + "url(" * 8000 + "</style>",
        '<p style="' + "url(" * 16000 + '">Water</p>',
        "<script>" + "1" * 64000 + "</script>",
        "<style>" + '"' * 60000 + "</style>",
    ],
    ids=[
        "unclosed css urls",
        "unclosed urls in an attribute",
        "a long run of digits",
        "unclosed css strings",
    ],
)
def test_long_hostile_markup_is_checked_in_linear_time(html: str) -> None:
    started = time.perf_counter()
    sandbox_problems(html, {})
    assert time.perf_counter() - started < 1.0
