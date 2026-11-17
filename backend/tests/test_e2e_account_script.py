import io
import sys
from types import ModuleType

import pytest

from app.core.roles import Capability, can, requires_two_factor
from app.schemas.admin import AccessRosterCreate
from app.schemas.auth import ForgotPasswordRequest
from app.scripts import provision_e2e_account, seed_admin
from app.scripts.operator_input import read_password
from app.services.e2e_account import E2E_ACCOUNT_EMAIL, E2E_ACCOUNT_ROLE
from app.services.password_accounts import operator_password_refusal

PASSWORD = "a-long-test-passphrase-41"


def test_the_e2e_address_passes_every_api_address_check() -> None:
    assert AccessRosterCreate(email=E2E_ACCOUNT_EMAIL).email == E2E_ACCOUNT_EMAIL
    assert ForgotPasswordRequest(email=E2E_ACCOUNT_EMAIL).email == E2E_ACCOUNT_EMAIL
    assert E2E_ACCOUNT_EMAIL == "e2e-researcher@kalavigyan.example"


def test_the_e2e_role_needs_no_two_step_and_may_ask() -> None:
    assert E2E_ACCOUNT_ROLE == "RESEARCHER"
    assert not requires_two_factor(E2E_ACCOUNT_ROLE)
    assert can(E2E_ACCOUNT_ROLE, Capability.ASK_STANDARD)
    assert not can(E2E_ACCOUNT_ROLE, Capability.MANAGE_ACCESS)


@pytest.mark.parametrize(("length", "refused"), [(11, True), (12, False), (200, False), (201, True)])
def test_operator_passwords_are_twelve_to_two_hundred_characters(length: int, refused: bool) -> None:
    assert (operator_password_refusal("p" * length) is not None) is refused


def test_a_piped_password_loses_only_its_line_ending(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("  spaced pass phrase  \r\nsecond line\n"))
    assert read_password() == "  spaced pass phrase  "


def test_provisioning_reads_the_password_from_stdin_and_never_prints_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    received: list[str] = []

    async def fake_run(password: str) -> str:
        received.append(password)
        return "created"

    monkeypatch.setattr(provision_e2e_account, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["provision_e2e_account"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"{PASSWORD}\n"))
    assert provision_e2e_account.main() == 0
    printed = capsys.readouterr()
    assert received == [PASSWORD]
    assert PASSWORD not in printed.out + printed.err
    assert E2E_ACCOUNT_EMAIL in printed.out
    assert "created" in printed.out


@pytest.mark.parametrize(("script", "entry"), [(provision_e2e_account, "run"), (seed_admin, "seed")])
def test_a_short_password_is_refused_before_the_database_and_not_echoed(
    script: ModuleType, entry: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def unreachable(password: str) -> str:
        raise AssertionError("the database must not be reached")

    short = "short-pass"
    monkeypatch.setattr(script, entry, unreachable)
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"{short}\n"))
    assert script.main() == 2
    printed = capsys.readouterr()
    assert short not in printed.out + printed.err
    assert "at least 12 characters" in printed.err
