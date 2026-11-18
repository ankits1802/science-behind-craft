import json
import sys
from typing import Any

import pytest

from app.core.roles import ADMIN, PROFESSOR
from app.scripts import provision_e2e_role_accounts as script
from app.services import two_factor
from app.services.e2e_account import E2E_ADMIN, E2E_PROFESSOR

VALUES = {
    "/kalavigyan/e2e/E2E_PROFESSOR_PASSWORD": "professor-long-passphrase-7",
    "/kalavigyan/e2e/E2E_PROFESSOR_TOTP_SECRET": two_factor.generate_secret(),
    "/kalavigyan/e2e/E2E_ADMIN_PASSWORD": "admin-long-passphrase-9",
    "/kalavigyan/e2e/E2E_ADMIN_TOTP_SECRET": two_factor.generate_secret(),
}


class AccessDenied(Exception):
    def __init__(self) -> None:
        super().__init__("User is not authorized; parameter text should never be shown")
        self.response = {"Error": {"Code": "AccessDeniedException", "Message": "hidden"}}


class FakeParameterStore:
    def __init__(
        self, values: dict[str, str], *, plain: frozenset[str] = frozenset(), error: Exception | None = None
    ):
        self.values = values
        self.plain = plain
        self.error = error
        self.requests: list[tuple[list[str], bool]] = []

    def get_parameters(self, *, Names: list[str], WithDecryption: bool) -> dict[str, Any]:
        self.requests.append((list(Names), WithDecryption))
        if self.error is not None:
            raise self.error
        rows = [
            {
                "Name": name,
                "Type": "String" if name in self.plain else "SecureString",
                "Value": self.values[name],
            }
            for name in Names
            if name in self.values
        ]
        return {"Parameters": rows, "InvalidParameters": [name for name in Names if name not in self.values]}


def printed(capsys: pytest.CaptureFixture[str]) -> str:
    out = capsys.readouterr()
    return out.out + out.err


def assert_no_value(text: str, values: dict[str, str]) -> None:
    for value in values.values():
        assert value not in text


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> FakeParameterStore:
    fake = FakeParameterStore(dict(VALUES))
    monkeypatch.setattr(script, "instance_role_client", lambda: fake)
    monkeypatch.setattr(sys, "argv", ["provision_e2e_role_accounts"])
    return fake


@pytest.fixture
def received(monkeypatch: pytest.MonkeyPatch) -> list[script.RoleCredentials]:
    seen: list[script.RoleCredentials] = []

    async def fake_run(credentials: list[script.RoleCredentials]) -> list[dict[str, Any]]:
        seen.extend(credentials)
        return [
            {"email": item.account.email, "role": item.account.role, "outcome": "created", "twoStep": True}
            for item in credentials
        ]

    monkeypatch.setattr(script, "run", fake_run)
    return seen


def test_the_script_reads_four_parameters_under_the_e2e_path() -> None:
    assert script.parameter_names() == list(VALUES)
    assert all(name.startswith("/kalavigyan/e2e/") for name in script.parameter_names())
    assert not any(name.startswith("/kalavigyan/env/") for name in script.parameter_names())


def test_provisioning_reads_parameter_store_and_prints_no_secret(
    store: FakeParameterStore, received: list[script.RoleCredentials], capsys: pytest.CaptureFixture[str]
) -> None:
    assert script.main() == 0
    text = printed(capsys)
    assert store.requests == [(list(VALUES), True)]
    assert [(item.account, item.password) for item in received] == [
        (E2E_PROFESSOR, VALUES["/kalavigyan/e2e/E2E_PROFESSOR_PASSWORD"]),
        (E2E_ADMIN, VALUES["/kalavigyan/e2e/E2E_ADMIN_PASSWORD"]),
    ]
    assert received[0].totp_secret == VALUES["/kalavigyan/e2e/E2E_PROFESSOR_TOTP_SECRET"]
    report = json.loads(text)
    assert report["ok"] is True
    assert [(row["email"], row["role"], row["twoStep"]) for row in report["accounts"]] == [
        (E2E_PROFESSOR.email, PROFESSOR, True),
        (E2E_ADMIN.email, ADMIN, True),
    ]
    assert_no_value(text, VALUES)
    assert_no_value(repr(received), VALUES)


def unreachable_run(monkeypatch: pytest.MonkeyPatch) -> None:
    async def unreachable(credentials: list[script.RoleCredentials]) -> list[dict[str, Any]]:
        raise AssertionError("the database must not be reached")

    monkeypatch.setattr(script, "run", unreachable)


def test_a_missing_parameter_is_named_and_nothing_is_provisioned(
    store: FakeParameterStore, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    unreachable_run(monkeypatch)
    del store.values["/kalavigyan/e2e/E2E_ADMIN_TOTP_SECRET"]
    assert script.main() == 2
    text = printed(capsys)
    assert "/kalavigyan/e2e/E2E_ADMIN_TOTP_SECRET" in text
    assert_no_value(text, VALUES)


def test_a_plain_string_parameter_is_refused(
    store: FakeParameterStore, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    unreachable_run(monkeypatch)
    store.plain = frozenset({"/kalavigyan/e2e/E2E_PROFESSOR_PASSWORD"})
    assert script.main() == 2
    text = printed(capsys)
    assert "SecureString" in text
    assert "/kalavigyan/e2e/E2E_PROFESSOR_PASSWORD" in text
    assert_no_value(text, VALUES)


@pytest.mark.parametrize(
    "case",
    [
        ("/kalavigyan/e2e/E2E_ADMIN_PASSWORD", "too-short-1", "at least 12 characters"),
        ("/kalavigyan/e2e/E2E_PROFESSOR_TOTP_SECRET", "not-base32-1890-not-base32", "base32"),
        ("/kalavigyan/e2e/E2E_ADMIN_TOTP_SECRET", "MFRGGZDFMZTWQ2LK", "at least 16 bytes"),
    ],
)
def test_a_weak_value_is_refused_by_name_and_never_echoed(
    case: tuple[str, str, str],
    store: FakeParameterStore,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    name, value, said = case
    unreachable_run(monkeypatch)
    store.values[name] = value
    assert script.main() == 2
    text = printed(capsys)
    assert f"{name}: " in text
    assert said in text
    assert value not in text
    assert_no_value(text, store.values)


def test_a_read_failure_names_the_error_code_only(
    store: FakeParameterStore, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    unreachable_run(monkeypatch)
    store.error = AccessDenied()
    assert script.main() == 2
    text = printed(capsys)
    assert "AccessDeniedException" in text
    assert "hidden" not in text
    assert "parameter text" not in text


def test_arguments_are_refused_and_never_echoed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    unreachable_run(monkeypatch)

    def no_client() -> None:
        raise AssertionError("Parameter Store must not be read")

    monkeypatch.setattr(script, "instance_role_client", no_client)
    monkeypatch.setattr(
        sys, "argv", ["provision_e2e_role_accounts", "--password", "typed-on-the-command-line"]
    )
    assert script.main() == 2
    text = printed(capsys)
    assert "takes no arguments" in text
    assert "typed-on-the-command-line" not in text


def test_the_parameter_client_skips_the_media_keys_in_the_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import botocore.session

    made: list[Any] = []
    real = botocore.session.get_session

    def recorded() -> Any:
        made.append(real())
        return made[-1]

    monkeypatch.setattr(botocore.session, "get_session", recorded)
    session = script.instance_role_session()
    methods = [provider.METHOD for provider in made[0].get_component("credential_provider").providers]
    assert "env" not in methods
    assert "iam-role" in methods
    assert session._session is made[0]
