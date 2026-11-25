import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from .fake_box import REPO, executable
from .git_history import GIT_ENV, STUBS, committed, git

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="the post-deploy check runs under Linux bash on the runner"
)

VERDICT = REPO / ".github" / "scripts" / "post_deploy_verdict.sh"
WORKFLOWS = REPO / ".github" / "workflows"
GRACE_SECONDS = 5400
SERVED_BEFORE = "e" * 40
CHECKS, BACKEND, WEB = "Backend checks", "Deploy backend", "Deploy web app"


@dataclass(frozen=True)
class Line:
    root: Path
    work: Path
    old: str
    head: str
    side: str


@dataclass(frozen=True)
class Said:
    code: int
    verdict: str
    out: str


def committed_at(work: Path, files: dict[str, str], hours_ago: float, monkeypatch: pytest.MonkeyPatch) -> str:
    when = f"{int(time.time() - hours_ago * 3600)} +0000"
    monkeypatch.setenv("GIT_COMMITTER_DATE", when)
    monkeypatch.setenv("GIT_AUTHOR_DATE", when)
    made = committed(work, files)
    monkeypatch.delenv("GIT_COMMITTER_DATE")
    monkeypatch.delenv("GIT_AUTHOR_DATE")
    return made


@pytest.fixture
def line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Line:
    work = tmp_path / "work"
    git(tmp_path, "init", "-q", "-b", "main", "work")
    base = committed_at(work, {"backend/app/routes.py": "ROUTES = ()\n"}, 4, monkeypatch)
    old = committed_at(work, {"backend/app/kilns.py": "KILNS = ('updraft',)\n"}, 3, monkeypatch)
    head = committed(work, {"docs/STATUS.md": "The batch is pushed.\n"})
    git(work, "checkout", "-q", "-b", "beside", base)
    side = committed_at(work, {"backend/app/glazes.py": "GLAZES = ()\n"}, 3, monkeypatch)
    git(work, "checkout", "-q", "main")
    commands = tmp_path / "bin"
    commands.mkdir()
    executable(STUBS / "gh.sh", commands / "gh")
    return Line(tmp_path, work, old, head, side)


def run(
    workflow: str, minutes_ago: float, head: str, *, event: str = "push", branch: str = "main"
) -> dict[str, str]:
    at = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return {
        "workflowName": workflow,
        "event": event,
        "headBranch": branch,
        "createdAt": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "headSha": head,
    }


def verdict(line: Line, runs: list[dict[str, str]], **asked: str) -> Said:
    output, summary, listed = line.root / "github-output", line.root / "summary.md", line.root / "runs.json"
    output.write_text("", encoding="utf-8")
    listed.write_text(json.dumps(runs), encoding="utf-8")
    wanted = {
        "MODE": "latest",
        "BUILT": "success",
        "EXPECTED": line.old,
        "HAVE": SERVED_BEFORE,
        "REACHED": "no",
    }
    env = {
        **os.environ,
        **GIT_ENV,
        **wanted,
        **asked,
        "PATH": f"{line.root / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "WAITED": "0",
        "GRACE_SECONDS": str(GRACE_SECONDS),
        "WEB_ORIGIN": "https://kalavigyan.example",
        "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(summary),
        "GITHUB_REPOSITORY": "example/kalavigyan",
        "RUNS": str(listed),
    }
    done = subprocess.run(
        ["bash", str(VERDICT)],
        cwd=line.work,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    decided = re.findall(r"^verdict=(.*)$", output.read_text(encoding="utf-8"), flags=re.MULTILINE)
    return Said(done.returncode, decided[-1] if decided else "", done.stdout + done.stderr)


def workflow_name(path: Path) -> str:
    named = re.search(r"^name: (.+)$", path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    assert named is not None, path
    return named.group(1)


def test_a_commit_older_than_the_grace_pushed_a_minute_ago_is_building(line: Line) -> None:
    said = verdict(line, [run(WEB, 1, line.head)])
    assert (said.code, said.verdict) == (0, "building"), said.out
    assert f"{line.old[:12]} reached main 1 minutes ago" in said.out


def test_a_backend_push_counts_from_its_checks_until_its_deploy_starts(line: Line) -> None:
    checking = verdict(line, [run(CHECKS, 2, line.head)])
    assert (checking.code, checking.verdict) == (0, "building"), checking.out
    deploying = verdict(line, [run(CHECKS, 80, line.head), run(BACKEND, 50, line.head, event="workflow_run")])
    assert (deploying.code, deploying.verdict) == (0, "building"), deploying.out
    assert "reached main 50 minutes ago" in deploying.out


def test_a_commit_whose_newest_run_started_past_the_grace_is_behind(line: Line) -> None:
    runs = [run(CHECKS, 150, line.head), run(BACKEND, 120, line.head, event="workflow_run")]
    said = verdict(line, runs)
    assert (said.code, said.verdict) == (1, "behind"), said.out
    assert "::error::production still serves" in said.out


def test_a_run_that_does_not_hold_the_commit_a_dispatched_check_or_another_branch_does_not_count(
    line: Line,
) -> None:
    runs = [
        run(WEB, 1, line.side),
        run(CHECKS, 1, line.head, event="workflow_dispatch"),
        run(WEB, 1, line.head, branch="beside"),
        run("Post-deploy check", 1, line.head, event="schedule"),
    ]
    said = verdict(line, runs)
    assert (said.code, said.verdict) == (1, "behind"), said.out
    assert "counted from its commit date" in said.out


def test_runs_that_cannot_be_read_leave_the_commit_date_to_judge(line: Line) -> None:
    old = verdict(line, [run(WEB, 1, line.head)], RUNS_UNREAD="yes")
    assert (old.code, old.verdict) == (1, "behind"), old.out
    assert "::warning::the runs of Deploy web app could not be read" in old.out
    young = verdict(line, [], RUNS_UNREAD="yes", EXPECTED=line.head)
    assert (young.code, young.verdict) == (0, "building"), young.out


@pytest.mark.parametrize(
    ("asked", "expected"),
    [
        ({"HAVE": ""}, (1, "silent")),
        ({"REACHED": "yes", "HAVE": "f" * 40}, (0, "served")),
        ({"MODE": "deploy", "BUILT": "none"}, (0, "no-build")),
        ({"MODE": "deploy", "BUILT": "failure"}, (1, "refused")),
        ({"MODE": "deploy"}, (1, "behind")),
        ({"MODE": "asked", "REACHED": "yes"}, (0, "served")),
    ],
)
def test_a_production_that_answers_or_a_named_deploy_is_judged_without_the_grace(
    line: Line, asked: dict[str, str], expected: tuple[int, str]
) -> None:
    said = verdict(line, [run(WEB, 1, line.head)], **asked)
    assert (said.code, said.verdict) == expected, said.out
    assert "reached main" not in said.out


def test_the_post_deploy_check_runs_the_verdict_with_a_token_that_reads_runs() -> None:
    text = (WORKFLOWS / "post-deploy.yml").read_text(encoding="utf-8")
    step = text[text.index("      - name: Say whether production serves it\n") : text.index("  pages:\n")]
    assert "          GH_TOKEN: ${{ github.token }}\n" in step
    assert f'          GRACE_SECONDS: "{GRACE_SECONDS}"\n' in step
    assert step.rstrip().endswith("run: bash .github/scripts/post_deploy_verdict.sh")
    served = text[text.index("  served:\n") : text.index("    steps:\n")]
    assert "      actions: read\n" in served


def test_the_runs_the_verdict_reads_are_the_workflows_that_bring_a_commit_to_production() -> None:
    script = VERDICT.read_text(encoding="utf-8")
    listed = re.search(r"^REACHING_RUNS=\(([^)]*)\)$", script, flags=re.MULTILINE)
    assert listed is not None
    names = {entry.split(":")[0] for entry in re.findall(r'"([^"]+)"', listed.group(1))}
    assert names == {CHECKS, BACKEND, WEB}
    assert names <= {workflow_name(path) for path in WORKFLOWS.glob("*.yml")}
    deploy_backend = (WORKFLOWS / "deploy-backend.yml").read_text(encoding="utf-8")
    assert f"    workflows: [{CHECKS}]\n" in deploy_backend
