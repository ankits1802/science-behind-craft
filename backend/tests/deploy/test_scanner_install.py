import re

from app.core.config import get_settings

from ..upload_scanners import EICAR
from .fake_box import REPO
from .test_release_wiring import DEPLOY, RELEASE, read

INSTALL = DEPLOY / "install_scanner.sh"
RUNBOOK = REPO / "docs" / "RUNBOOK.md"


def shell_value(name: str) -> str:
    found = re.search(rf"^{name}=(.+)$", read(INSTALL), re.MULTILINE)
    assert found is not None, name
    return found.group(1).strip("'\"")


def test_every_release_installs_the_scanner_after_the_browser_and_before_the_build_as_a_warning() -> None:
    release = read(RELEASE)
    steps = (
        'bash "$HERE/install_renderer.sh"',
        'bash "$HERE/install_scanner.sh" || say "::warning::',
        "build_release\n",
    )
    order = [release.index(step) for step in steps]
    assert order == sorted(order)
    assert "every upload is refused until it is" in release


def test_the_scanner_is_clamd_from_ubuntu_s_packages_at_the_socket_the_api_reads() -> None:
    script = read(INSTALL)
    assert shell_value("PACKAGES") == "(clamav-daemon clamav-freshclam clamdscan)"
    assert shell_value("SOCKET") == get_settings().malware_scan_socket == "/var/run/clamav/clamd.ctl"
    assert 'grep -q "^LocalSocket ${SOCKET}\\$" "$CONF"' in script
    assert "apt-get install -y --no-install-recommends" in script


def test_clamd_holds_one_copy_of_its_signatures_under_a_memory_ceiling_and_restarts() -> None:
    script = read(INSTALL)
    assert "set_option ConcurrentDatabaseReload no" in script
    assert shell_value("MEMORY_MAX") == "2G"
    assert "MemoryMax=%s\\nRestart=on-failure" in script
    assert shell_value("DROP_IN") == "/etc/systemd/system/clamav-daemon.service.d/kalavigyan.conf"


def test_signatures_come_from_freshclam_and_the_release_proves_a_clean_pass_and_an_eicar_find() -> None:
    script = read(INSTALL)
    assert "systemctl enable --now clamav-freshclam" in script
    assert shell_value("EICAR_HEAD") + shell_value("EICAR_TAIL") == EICAR
    assert EICAR not in script
    assert "clamdscan --no-summary --stream -" in script and "*FOUND*)" in script


def test_the_runbook_says_how_the_scanner_runs_and_what_a_down_scanner_does() -> None:
    section = read(RUNBOOK).split("\n## Upload scanner\n", 1)[1].split("\n## ", 1)[0]
    for named in (
        "install_scanner.sh",
        "clamav-daemon",
        "clamav-freshclam",
        "ConcurrentDatabaseReload no",
        "MemoryMax 2G",
        "MALWARE_SCAN_SOCKET",
        "503",
        "journalctl -u clamav-daemon",
    ):
        assert named in section, named
