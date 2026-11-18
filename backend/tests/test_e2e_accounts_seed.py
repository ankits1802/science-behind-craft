import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from app.scripts.provision_e2e_role_accounts import PARAMETER_PATH, parameter_names
from app.services.e2e_account import E2E_ROLE_ACCOUNTS, totp_secret_refusal
from app.services.password_accounts import operator_password_refusal

SEED = Path(__file__).resolve().parents[2] / "infra" / "scripts" / "seed_e2e_accounts.py"


def load_seed() -> ModuleType:
    spec = importlib.util.spec_from_file_location("seed_e2e_accounts", SEED)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed = load_seed()


class FakeParameters:
    def __init__(self, stored: dict[str, str] | None = None) -> None:
        self.stored = dict(stored or {})
        self.written: list[str] = []

    def get(self, name: str) -> str | None:
        return self.stored.get(name)

    def put(self, name: str, value: str) -> None:
        self.written.append(name)
        self.stored[name] = value


class FakeGitHub:
    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    def __call__(self, name: str, value: str) -> None:
        self.secrets[name] = value


def every_secret_name() -> set[str]:
    return {
        account.secret_name(part)
        for account in E2E_ROLE_ACCOUNTS
        for part in ("EMAIL", "PASSWORD", "TOTP_SECRET")
    }


def test_the_seed_names_match_what_the_box_reads_and_the_run_signs_in_as() -> None:
    assert seed.PARAMETER_PATH == PARAMETER_PATH
    assert {account.role: account.email for account in E2E_ROLE_ACCOUNTS} == seed.ACCOUNTS
    params = FakeParameters()
    seed.settle(params, rotate=False)
    assert sorted(params.written) == sorted(parameter_names())


def test_generated_values_pass_the_box_checks() -> None:
    for _ in range(20):
        assert operator_password_refusal(seed.new_password()) is None
        assert totp_secret_refusal(seed.new_totp_secret()) is None


def test_a_first_run_stores_every_value_once_and_prints_none(capsys: pytest.CaptureFixture[str]) -> None:
    params, github = FakeParameters(), FakeGitHub()
    assert seed.main([], params=params, set_secret=github) == 0
    printed = capsys.readouterr()
    text = printed.out + printed.err
    assert set(github.secrets) == every_secret_name()
    for account in E2E_ROLE_ACCOUNTS:
        for part in ("PASSWORD", "TOTP_SECRET"):
            name = account.secret_name(part)
            assert github.secrets[name] == params.stored[f"{PARAMETER_PATH}/{name}"]
            assert github.secrets[name] not in text
        assert github.secrets[account.secret_name("EMAIL")] == account.email
    assert "sha256" in text


def test_a_second_run_keeps_the_stored_values_and_rotate_replaces_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    params, github = FakeParameters(), FakeGitHub()
    seed.main([], params=params, set_secret=github)
    first = dict(params.stored)
    params.written.clear()
    seed.main([], params=params, set_secret=github)
    assert params.written == []
    assert params.stored == first
    seed.main(["--rotate"], params=params, set_secret=github)
    assert sorted(params.written) == sorted(parameter_names())
    assert all(params.stored[name] != first[name] for name in first)
    printed = capsys.readouterr()
    for value in (*first.values(), *params.stored.values()):
        assert value not in printed.out + printed.err


def test_skip_github_writes_parameter_store_only() -> None:
    params, github = FakeParameters(), FakeGitHub()
    seed.main(["--skip-github"], params=params, set_secret=github)
    assert github.secrets == {}
    assert len(params.stored) == len(parameter_names())
