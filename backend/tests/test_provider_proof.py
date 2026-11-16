import ast
import time
import uuid
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.main import app
from app.models import User
from app.schemas.auth import ChangePasswordRequest
from app.services import google_auth, oidc_sign_in, provider_proof
from app.services.oidc_sign_in import CodeGrant
from app.services.provider_proof import ProofRefused, ProviderProof, issued_recently, require_fresh_proof
from tests.google_fake import GOOGLE_CLIENT_ID, FakeGoogle
from tests.oidc_fake_idp import REDIRECT_URI, VERIFIER, YAHOO_CLIENT_ID, FakeIdP, login_body
from tests.test_app_and_schema import MIGRATIONS, enum_additions, initial_enum_list, module_constant

NOW = 1_800_000_000.0


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class NonceBook:
    def __init__(self) -> None:
        self.issued: dict[str, tuple[str, Any]] = {}
        self.spent: set[str] = set()

    def issue(self, raw: str, *, purpose: str = "FIRST_PASSWORD", user_id: Any = None) -> str:
        self.issued[raw] = (purpose, user_id)
        return raw

    async def consume(self, _session: Any, raw: str, *, purpose: str, user_id: Any = None) -> bool:
        if raw in self.spent or raw not in self.issued:
            return False
        issued_purpose, issued_user = self.issued[raw]
        if issued_purpose != purpose or (user_id is not None and issued_user != user_id):
            return False
        self.spent.add(raw)
        return True


@pytest.fixture
def book(monkeypatch: pytest.MonkeyPatch) -> NonceBook:
    nonces = NonceBook()
    monkeypatch.setattr(google_auth, "consume_nonce", nonces.consume)
    monkeypatch.setattr(oidc_sign_in, "consume_nonce", nonces.consume)
    return nonces


@pytest.fixture
def google(monkeypatch: pytest.MonkeyPatch) -> FakeGoogle:
    return FakeGoogle().install(monkeypatch)


@pytest.fixture
def idp(monkeypatch: pytest.MonkeyPatch) -> FakeIdP:
    return FakeIdP().install(monkeypatch)


def account(provider: str, email: str = "meera.iyer@example.com") -> User:
    return User(id=uuid.uuid4(), email=email, name="Meera Iyer", authProvider=provider, passwordHash=None)


def yahoo_grant(nonce: str, *, code: str = "the-code") -> CodeGrant:
    return CodeGrant("YAHOO", code, VERIFIER, REDIRECT_URI, nonce)


async def refusal(person: User, proof: ProviderProof, *, now: float | None = None) -> ProofRefused:
    with pytest.raises(ProofRefused) as caught:
        await require_fresh_proof(FakeSession(), person, proof, now=now)
    return caught.value


async def test_a_google_only_account_is_confirmed_by_a_fresh_google_proof(
    book: NonceBook, google: FakeGoogle
) -> None:
    person = account("GOOGLE", "Meera.Iyer@Example.com")
    nonce = book.issue("nonce-google-fresh", user_id=person.id)
    token = google.mint("meera.iyer@example.com", nonce, iat=NOW - 60)
    session = FakeSession()
    proved_by = await require_fresh_proof(session, person, ProviderProof(google_id_token=token), now=NOW)
    assert proved_by == "GOOGLE"
    assert book.spent == {"nonce-google-fresh"}
    assert session.commits == 1


async def test_a_yahoo_account_is_confirmed_by_a_fresh_yahoo_code(book: NonceBook, idp: FakeIdP) -> None:
    person = account("YAHOO", "ravi@yahoo.com")
    nonce = book.issue("nonce-yahoo-fresh-0123456789", user_id=person.id)
    idp.issue(idp.sign(idp.yahoo_claims("Ravi@Yahoo.com", raw_nonce=nonce), alg="ES256"))
    proved_by = await require_fresh_proof(FakeSession(), person, ProviderProof(grant=yahoo_grant(nonce)))
    assert proved_by == "YAHOO"
    assert [url for url, _form in idp.redemptions] == ["https://api.login.yahoo.com/oauth2/get_token"]
    assert idp.redemptions[0][1]["client_id"] == YAHOO_CLIENT_ID


async def test_a_google_proof_of_another_address_is_refused(book: NonceBook, google: FakeGoogle) -> None:
    person = account("GOOGLE")
    nonce = book.issue("nonce-google-other", user_id=person.id)
    token = google.mint("somebody-else@example.com", nonce, iat=NOW)
    refused = await refusal(person, ProviderProof(google_id_token=token), now=NOW)
    assert (refused.provider, refused.reason) == ("GOOGLE", "another-address")


async def test_a_google_address_google_has_not_verified_is_refused(
    book: NonceBook, google: FakeGoogle
) -> None:
    person = account("GOOGLE")
    nonce = book.issue("nonce-google-unverified", user_id=person.id)
    token = google.mint(person.email, nonce, iat=NOW, verified=False)
    refused = await refusal(person, ProviderProof(google_id_token=token), now=NOW)
    assert (refused.provider, refused.reason) == ("GOOGLE", "email_unverified")


async def test_a_yahoo_proof_of_another_address_is_refused(book: NonceBook, idp: FakeIdP) -> None:
    person = account("YAHOO", "ravi@yahoo.com")
    nonce = book.issue("nonce-yahoo-other-0123456789", user_id=person.id)
    idp.issue(idp.sign(idp.yahoo_claims("someone-else@yahoo.com", raw_nonce=nonce)))
    refused = await refusal(person, ProviderProof(grant=yahoo_grant(nonce)))
    assert (refused.provider, refused.reason) == ("YAHOO", "another-address")


async def test_a_proof_from_another_provider_spends_and_redeems_nothing(
    book: NonceBook, google: FakeGoogle, idp: FakeIdP
) -> None:
    yahoo_person = account("YAHOO")
    nonce = book.issue("nonce-another-provider-01234", user_id=yahoo_person.id)
    token = google.mint(yahoo_person.email, nonce, iat=NOW)
    refused = await refusal(yahoo_person, ProviderProof(google_id_token=token), now=NOW)
    assert (refused.provider, refused.reason) == ("GOOGLE", "another-provider")
    google_person = account("GOOGLE")
    refused = await refusal(google_person, ProviderProof(grant=yahoo_grant(nonce)))
    assert (refused.provider, refused.reason) == ("YAHOO", "another-provider")
    assert book.spent == set()
    assert idp.redemptions == []


async def test_a_google_nonce_confirms_once(book: NonceBook, google: FakeGoogle) -> None:
    person = account("GOOGLE")
    nonce = book.issue("nonce-google-once", user_id=person.id)
    token = google.mint(person.email, nonce, iat=NOW)
    assert await require_fresh_proof(FakeSession(), person, ProviderProof(google_id_token=token), now=NOW)
    refused = await refusal(person, ProviderProof(google_id_token=token), now=NOW)
    assert (refused.provider, refused.reason) == ("GOOGLE", "nonce_reused_or_unknown")


async def test_a_yahoo_nonce_confirms_once_and_is_redeemed_once(book: NonceBook, idp: FakeIdP) -> None:
    person = account("YAHOO", "ravi@yahoo.com")
    nonce = book.issue("nonce-yahoo-once-0123456789", user_id=person.id)
    idp.issue(idp.sign(idp.yahoo_claims("ravi@yahoo.com", raw_nonce=nonce)))
    assert await require_fresh_proof(FakeSession(), person, ProviderProof(grant=yahoo_grant(nonce)))
    refused = await refusal(person, ProviderProof(grant=yahoo_grant(nonce, code="the-code-again")))
    assert (refused.provider, refused.reason) == ("YAHOO", "nonce-unknown-or-spent")
    assert len(idp.redemptions) == 1


@pytest.mark.parametrize(
    ("purpose", "owner"),
    [("GOOGLE_SIGN_IN", None), ("GOOGLE_LINK", "same"), ("FIRST_PASSWORD", "other")],
)
async def test_only_a_first_password_nonce_of_this_account_confirms(
    book: NonceBook, google: FakeGoogle, purpose: str, owner: str | None
) -> None:
    person = account("GOOGLE")
    user_id = {None: None, "same": person.id, "other": uuid.uuid4()}[owner]
    nonce = book.issue(f"nonce-{purpose}-{owner}", purpose=purpose, user_id=user_id)
    token = google.mint(person.email, nonce, iat=NOW)
    refused = await refusal(person, ProviderProof(google_id_token=token), now=NOW)
    assert refused.reason == "nonce_reused_or_unknown"


async def test_a_google_token_issued_six_minutes_ago_is_stale(book: NonceBook, google: FakeGoogle) -> None:
    person = account("GOOGLE")
    nonce = book.issue("nonce-google-stale", user_id=person.id)
    token = google.mint(person.email, nonce, iat=NOW - 360)
    refused = await refusal(person, ProviderProof(google_id_token=token), now=NOW)
    assert (refused.provider, refused.reason) == ("GOOGLE", "stale")


async def test_a_yahoo_token_issued_ten_minutes_ago_is_stale(book: NonceBook, idp: FakeIdP) -> None:
    person = account("YAHOO", "ravi@yahoo.com")
    nonce = book.issue("nonce-yahoo-stale-0123456789", user_id=person.id)
    issued = int(time.time()) - 600
    idp.issue(idp.sign(idp.yahoo_claims("ravi@yahoo.com", raw_nonce=nonce, iat=issued)))
    refused = await refusal(person, ProviderProof(grant=yahoo_grant(nonce)))
    assert (refused.provider, refused.reason) == ("YAHOO", "stale")


async def test_no_proof_is_refused_naming_the_accounts_provider(book: NonceBook) -> None:
    refused = await refusal(account("YAHOO"), ProviderProof())
    assert (refused.provider, refused.reason) == ("YAHOO", "no-proof")


async def test_an_account_without_a_provider_cannot_be_confirmed(book: NonceBook, google: FakeGoogle) -> None:
    person = account("LOCAL")
    nonce = book.issue("nonce-local", user_id=person.id)
    token = google.mint(person.email, nonce, iat=NOW)
    refused = await refusal(person, ProviderProof(google_id_token=token), now=NOW)
    assert refused.reason == "no-provider"
    assert book.spent == set()


@pytest.mark.parametrize(
    ("issued_at", "fresh"),
    [
        (NOW, True),
        (NOW - 300, True),
        (NOW - 301, False),
        (NOW + 60, True),
        (NOW + 61, False),
        (int(NOW) - 10, True),
        (True, False),
        (None, False),
        (str(int(NOW)), False),
    ],
)
def test_fresh_means_issued_within_five_minutes_and_at_most_a_minute_ahead(
    issued_at: Any, fresh: bool
) -> None:
    assert issued_recently(issued_at, NOW) is fresh


def test_the_account_provider_is_google_microsoft_or_yahoo() -> None:
    assert provider_proof.CONFIRM_PROVIDERS == ("GOOGLE", "MICROSOFT", "YAHOO")
    assert [provider_proof.account_provider(account(name)) for name in ("LOCAL", "GOOGLE", "YAHOO")] == [
        None,
        "GOOGLE",
        "YAHOO",
    ]


def test_each_provider_names_its_own_client_id(google: FakeGoogle, idp: FakeIdP) -> None:
    assert provider_proof.client_id_for("GOOGLE") == GOOGLE_CLIENT_ID
    assert provider_proof.client_id_for("YAHOO") == YAHOO_CLIENT_ID


def test_a_change_password_body_carries_one_whole_proof() -> None:
    plain = ChangePasswordRequest(newPassword="a-new-password-1")
    assert (plain.googleIdToken, plain.has_oidc_code) == (None, False)
    assert ChangePasswordRequest(newPassword="a-new-password-1", **login_body("YAHOO")).has_oidc_code
    with pytest.raises(ValidationError):
        ChangePasswordRequest(newPassword="a-new-password-1", googleIdToken="t", **login_body("YAHOO"))
    with pytest.raises(ValidationError):
        ChangePasswordRequest(newPassword="a-new-password-1", **{**login_body("YAHOO"), "oidcCode": None})
    with pytest.raises(ValidationError):
        ChangePasswordRequest(newPassword="a-new-password-1", **login_body("GOOGLE"))


def test_the_migration_adds_first_password_and_its_downgrade_restores_the_three_before() -> None:
    later = ast.parse((MIGRATIONS / "0011_first_password_proof.py").read_text(encoding="utf-8"))
    assert module_constant(later, "AUTH_NONCE_PURPOSES_BEFORE") == (
        "GOOGLE_SIGN_IN",
        "GOOGLE_LINK",
        "OIDC_SIGN_IN",
    )
    assert initial_enum_list()["AuthNoncePurpose"] + ("OIDC_SIGN_IN",) == (
        "GOOGLE_SIGN_IN",
        "GOOGLE_LINK",
        "OIDC_SIGN_IN",
    )
    assert enum_additions()["AuthNoncePurpose"] == ("OIDC_SIGN_IN", "FIRST_PASSWORD")
    assert provider_proof.NONCE_PURPOSE == "FIRST_PASSWORD"


async def test_the_first_password_routes_need_a_session() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        nonce = await client.post("/api/auth/first-password/nonce")
        change = await client.post(
            "/api/auth/change-password", json={"newPassword": "a-new-password-1", **login_body("YAHOO")}
        )
    assert (nonce.status_code, change.status_code) == (401, 401)
