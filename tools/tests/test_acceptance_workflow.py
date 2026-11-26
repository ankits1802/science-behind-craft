from __future__ import annotations

import re
from typing import Any

import yaml
from acceptance_support import REPO

WORKFLOW = REPO / ".github" / "workflows" / "agent-acceptance.yml"
PINNED = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
PROFESSOR = {"E2E_PROFESSOR_EMAIL", "E2E_PROFESSOR_PASSWORD", "E2E_PROFESSOR_TOTP_SECRET"}


def workflow() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def steps() -> list[dict[str, Any]]:
    return workflow()["jobs"]["run"]["steps"]


def named(fragment: str) -> dict[str, Any]:
    found = [step for step in steps() if fragment in step.get("name", "")]
    assert len(found) == 1, fragment
    return found[0]


def steps_given(name: str) -> list[str]:
    return [step["name"] for step in steps() if name in (step.get("env") or {})]


def test_the_workflow_parses_and_runs_only_when_dispatched_by_hand() -> None:
    triggers = workflow()[True]
    assert set(triggers) == {"workflow_dispatch"}
    assert workflow()["permissions"] == {"contents": "read"}
    assert workflow()["jobs"]["run"]["if"] == "github.repository == 'cxacraftecosystem-ui/KalaVigyan'"


def test_the_inputs_are_the_craft_the_request_the_cap_and_the_model_with_the_brief_s_defaults() -> None:
    inputs = workflow()[True]["workflow_dispatch"]["inputs"]
    assert {name: entry["default"] for name, entry in inputs.items()} == {
        "craft": "Sanganeri-Hand-Block-Printing",
        "request": "Deepen this craft's page to the KalaVigyan bar.",
        "cap": "12",
        "model": "claude-opus-5-5",
    }


def test_no_script_interpolates_an_input_and_the_run_reads_them_from_its_environment() -> None:
    for step in steps():
        assert "${{" not in step.get("run", ""), step["name"]
    run = named("MCP connector")
    assert {name: run["env"][name] for name in ("CRAFT", "REQUEST", "CAP", "MODEL")} == {
        "CRAFT": "${{ inputs.craft }}",
        "REQUEST": "${{ inputs.request }}",
        "CAP": "${{ inputs.cap }}",
        "MODEL": "${{ inputs.model }}",
    }
    assert run["run"].startswith("backend/.venv/bin/python tools/agent_acceptance.py run ")
    assert '--token-file "$ACCEPTANCE_TOKEN_FILE" --out "$RUN_DIR"' in run["run"]


def test_the_api_key_and_the_professor_s_secrets_reach_only_the_steps_that_need_them() -> None:
    assert steps_given("ANTHROPIC_API_KEY") == [
        "Check the secrets and the API variable",
        "Let the model build the page through the API's MCP connector",
    ]
    for secret in PROFESSOR:
        assert steps_given(secret) == [
            "Check the secrets and the API variable",
            "Sign the Professor in through the consent page, as a contributor's MCP client does",
        ]
    assert "--project=agent-acceptance" in named("Sign the Professor in")["run"]


def test_the_token_stays_outside_the_artifact_and_the_connection_is_always_revoked() -> None:
    check = named("Check the secrets")["run"]
    assert 'echo "ACCEPTANCE_TOKEN_FILE=$RUNNER_TEMP/agent-acceptance-token.json" >> "$GITHUB_ENV"' in check
    revoke = named("Revoke the run's MCP connection")
    assert revoke["if"] == "always()"
    assert 'tools/agent_acceptance.py revoke --token-file "$ACCEPTANCE_TOKEN_FILE"' in revoke["run"]
    kept = named("Keep what the model made")
    assert kept["if"] == "always()"
    assert kept["with"]["path"] == "${{ env.RUN_DIR }}"
    assert workflow()["jobs"]["run"]["env"]["RUN_DIR"] == "agent-acceptance-run"
    order = [step["name"] for step in steps()]
    assert order.index("Revoke the run's MCP connection") < order.index("Keep what the model made")


def test_the_summary_is_shown_whatever_happened_and_every_action_is_pinned() -> None:
    said = named("Say what the model made")
    assert said["if"] == "always()"
    assert 'cat "$RUN_DIR/summary.md" >> "$GITHUB_STEP_SUMMARY"' in said["run"]
    for step in steps():
        if "uses" in step:
            assert PINNED.match(step["uses"]), step["uses"]
