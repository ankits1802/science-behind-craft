import re

from app.core.config import get_settings
from app.renderer.settings import BROWSER_PATH, RENDERER_PORT

from .fake_box import REPO, SWITCH
from .test_release_wiring import DEPLOY, RELEASE, UNITS, read, service

UNIT = UNITS / "kv-renderer.service"
PIN = DEPLOY / "chromium.pin"
INSTALL = DEPLOY / "install_renderer.sh"
RENDER_ENV = DEPLOY / "render_env.sh"
RUNBOOK = REPO / "docs" / "RUNBOOK.md"
PRIVATE_RANGES = {"169.254.0.0/16", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10"}


def pinned(name: str) -> str:
    found = re.search(rf"^{name}=(\S+)$", read(PIN), re.MULTILINE)
    assert found is not None, name
    return found.group(1)


def test_the_renderer_runs_its_own_process_under_a_memory_ceiling_that_never_swaps() -> None:
    unit = service(UNIT)
    assert unit["ExecStart"] == ["/opt/kalavigyan/current/backend/.venv/bin/python -m app.renderer"]
    assert (unit["MemoryHigh"], unit["MemoryMax"], unit["MemorySwapMax"]) == (["1200M"], ["1536M"], ["0"])
    assert unit["TasksMax"] == ["512"] and unit["KillMode"] == ["control-group"]
    assert "Environment=KV_PROCESS=renderer" in read(UNIT) and unit["SyslogIdentifier"] == ["kv-renderer"]


def test_the_renderer_is_sandboxed_as_the_fetcher_is_and_never_reads_the_api_s_secrets() -> None:
    unit = service(UNIT)
    assert (unit["DynamicUser"], unit["ProtectProc"], unit["ProtectSystem"]) == (
        ["yes"],
        ["invisible"],
        ["strict"],
    )
    for shared in ("User", "Group", "SupplementaryGroups"):
        assert shared not in unit, shared
    assert unit["EnvironmentFile"] == ["/opt/kalavigyan/renderer.env"]
    assert {"-/opt/kalavigyan/.env", "-/opt/kalavigyan/fetcher.env"} <= set(
        unit["InaccessiblePaths"][0].split()
    )
    assert set(unit["IPAddressDeny"][0].split()) >= PRIVATE_RANGES
    assert set(service(UNITS / "kv-fetcher.service")["IPAddressDeny"][0].split()) >= PRIVATE_RANGES
    assert unit["NoNewPrivileges"] == ["yes"] and unit["RestrictNamespaces"] == ["yes"]


def test_the_api_the_unit_and_the_renderer_agree_on_its_address_and_its_browser() -> None:
    unit = read(UNIT)
    assert (
        f"Environment=RENDERER_PORT={RENDERER_PORT}\n" in unit
        and "Environment=RENDERER_HOST=127.0.0.1\n" in unit
    )
    assert get_settings().renderer_url == f"http://127.0.0.1:{RENDERER_PORT}"
    assert f"Environment=RENDERER_BROWSER={BROWSER_PATH}\n" in unit
    assert BROWSER_PATH == "/opt/chrome-headless-shell/current/chrome-headless-shell"
    assert 'ln -sfn "$TARGET" "$BROWSERS/current.tmp"' in read(INSTALL)


def test_the_browser_is_the_pinned_headless_shell_checked_against_its_sha256() -> None:
    version = pinned("CHROME_VERSION")
    assert re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version)
    assert pinned("CHROME_URL") == (
        f"https://storage.googleapis.com/chrome-for-testing-public/{version}/linux64/chrome-headless-shell-linux64.zip"
    )
    assert re.fullmatch(r"[0-9a-f]{64}", pinned("CHROME_SHA256"))
    install = read(INSTALL)
    assert 'echo "${CHROME_SHA256}  $stage/shell.zip" | sha256sum -c -' in install
    assert "ldd" in install and "not found" in install


def test_every_release_installs_the_browser_after_its_logs_and_restarts_the_renderer_with_the_workers() -> (
    None
):
    release = read(RELEASE)
    steps = (
        'bash "$HERE/ship_logs.sh"',
        'bash "$HERE/install_renderer.sh" || say "::warning::',
        "build_release\n  name_release\n",
    )
    order = [release.index(step) for step in steps]
    assert order == sorted(order)
    assert "WORKERS=(kv-worker kv-fetcher kv-contributions kv-renderer)\n" in read(SWITCH)


def test_the_renderer_s_environment_holds_only_its_own_keys_and_the_site() -> None:
    script = read(RENDER_ENV)
    assert 'k.startswith("RENDERER_") or k in {"APP_ENV", "LOG_LEVEL", "PUBLIC_WEB_URL"}' in script
    assert 'place "$work/renderer.env" "$APP/renderer.env"' in script


def test_the_runbook_says_how_the_renderer_runs_and_what_to_do_when_it_is_down() -> None:
    runbook = read(RUNBOOK)
    section = runbook.split("\n## Page renderer\n", 1)[1].split("\n## ", 1)[0]
    for named in (
        "kv-renderer",
        "chromium.pin",
        "install_renderer.sh",
        "MemoryMax 1536M",
        "8091",
        "journalctl -u kv-renderer",
    ):
        assert named in section, named


def test_a_library_ubuntu_renamed_with_t64_is_installed_by_its_new_name_and_found_without_a_broken_pipe() -> (
    None
):
    script = read(INSTALL)
    candidate = script[script.index("candidate() {") : script.index("resolved() {")]
    resolved = script[script.index("resolved() {") : script.index("install_libraries() {")]
    assert '"$(apt-cache policy "$1" 2>/dev/null)"' in candidate and "| grep" not in candidate
    assert 'candidate "${name}t64"' in resolved and 'name="${name}t64"' in resolved
    assert "wanted_libraries | resolved" in script
