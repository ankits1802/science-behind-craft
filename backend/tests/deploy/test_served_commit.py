import os
import subprocess
import sys
from pathlib import Path

import pytest

from .fake_box import REPO
from .git_history import GIT_ENV, History, made_history

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="the wait for production runs under Linux bash on the runner"
)

SERVED = REPO / ".github" / "actions" / "await-build" / "served.sh"
ACTION = REPO / ".github" / "actions" / "await-build" / "action.yml"
WORKFLOWS = REPO / ".github" / "workflows"
API = "https://api.example.org"
AWAITED = "        uses: ./.github/actions/await-build\n"
API_INPUT = "          api-origin: ${{ vars.API_BASE_URL }}\n"


@pytest.fixture
def history(tmp_path: Path) -> History:
    return made_history(tmp_path)


def read(history: History, expected: str, web: str, api: str, *, api_origin: str = API) -> dict[str, str]:
    output = history.root / "github-output"
    output.write_text("", encoding="utf-8")
    env = {
        **os.environ,
        **GIT_ENV,
        "PATH": f"{history.root / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "GITHUB_OUTPUT": str(output),
        "BUILT": "success",
        "EXPECTED": expected,
        "ORIGIN": "https://kalavigyan.example",
        "API_ORIGIN": api_origin,
        "WAIT_SECONDS": "0",
        "WEB_COMMIT": web,
        "LIVE_RELEASE": api,
    }
    done = subprocess.run(
        ["bash", str(SERVED)],
        cwd=history.checkout,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    lines = output.read_text(encoding="utf-8").splitlines()
    return dict(line.split("=", 1) for line in lines)


def test_a_build_is_served_once_the_api_runs_its_release_or_a_later_one(history: History) -> None:
    assert read(history, history.api, history.api, history.api)["reached"] == "yes"
    assert read(history, history.api, history.api, history.web)["reached"] == "yes"
    said = read(history, history.api, history.web, history.api)
    assert (said["served"], said["api"], said["reached"]) == (history.web, history.api, "yes")


def test_a_web_only_build_is_served_by_the_api_it_changes_nothing_of(history: History) -> None:
    assert read(history, history.web, history.web, history.api)["reached"] == "yes"


def test_a_build_whose_api_has_not_shipped_is_not_served_yet(history: History) -> None:
    assert read(history, history.api, history.api, history.first)["reached"] == "no"
    assert read(history, history.web, history.web, history.first)["reached"] == "no"


def test_an_api_that_names_no_release_or_does_not_answer_holds_the_check(history: History) -> None:
    for api in ("dev", "unreachable"):
        said = read(history, history.api, history.api, api)
        assert (said["api"], said["reached"]) == ("" if api == "unreachable" else api, "no"), api


def test_without_an_api_origin_only_the_site_is_read(history: History) -> None:
    said = read(history, history.api, history.api, history.first, api_origin="")
    assert (said["api"], said["reached"]) == ("", "yes")
    assert read(history, history.api, history.first, history.api, api_origin="")["reached"] == "no"


def test_both_checks_after_a_deploy_wait_for_the_api_as_well_as_the_site() -> None:
    assert 'run: bash "$GITHUB_ACTION_PATH/served.sh"' in ACTION.read_text(encoding="utf-8")
    for workflow in ("post-deploy.yml", "monograph-parity.yml"):
        text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
        step = text[text.index(AWAITED) :]
        assert text.count(AWAITED) == 1, workflow
        assert API_INPUT in step[: step.index("      - name:")], workflow
