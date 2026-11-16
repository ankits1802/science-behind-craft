import ast
import logging
import time
from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import ValidationError

from app.main import app
from app.schemas.auth import LoginRequest
from app.services import oidc_sign_in
from app.services.oidc_sign_in import MICROSOFT, YAHOO, EmailNotVerified, SignInRefused
from tests.oidc_fake_idp import (
    MICROSOFT_CLIENT_ID,
    RAW_NONCE,
    REDIRECT_URI,
    VERIFIER,
    WORK_TENANT,
    YAHOO_CLIENT_ID,
    YAHOO_SECRET,
    FakeIdP,
    fake_settings,
    login_body,
)
from tests.test_app_and_schema import MIGRATIONS, enum_additions, initial_enum_list, module_constant


@pytest.fixture
def idp(monkeypatch: pytest.MonkeyPatch) -> FakeIdP:
    return FakeIdP().install(monkeypatch)


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _verify(name: str, token: str, *, raw_nonce: str = RAW_NONCE, now: float | None = None) -> dict:
    p = oidc_sign_in.provider(name)
    assert p is not None
    return await oidc_sign_in.verify_id_token(p, token, raw_nonce=raw_nonce, now=now)


async def _refusal(name: str, token: str, **kwargs: object) -> str:
    with pytest.raises(SignInRefused) as caught:
        await _verify(name, token, **kwargs)
    return caught.value.reason


async def test_a_genuine_microsoft_token_is_accepted(idp: FakeIdP) -> None:
    claims = await _verify(MICROSOFT, idp.sign(idp.microsoft_claims("meera@outlook.com")))
    assert claims["email"] == "meera@outlook.com"


async def test_a_genuine_yahoo_token_signed_es256_is_accepted(idp: FakeIdP) -> None:
    claims = await _verify(YAHOO, idp.sign(idp.yahoo_claims("ravi@yahoo.com"), alg="ES256"))
    assert claims["aud"] == YAHOO_CLIENT_ID


async def test_keys_are_cached_and_an_unknown_key_inside_a_minute_is_refused(idp: FakeIdP) -> None:
    token = idp.sign(idp.yahoo_claims("ravi@yahoo.com"))
    await _verify(YAHOO, token)
    await _verify(YAHOO, token)
    assert idp.jwks_fetches == 1
    rotated = idp.sign(idp.yahoo_claims("ravi@yahoo.com"), kid="rotated")
    assert await _refusal(YAHOO, rotated) == "unknown-key"
    assert idp.jwks_fetches == 1


async def test_a_token_signed_by_an_unpublished_key_is_refused(idp: FakeIdP) -> None:
    token = idp.sign(idp.yahoo_claims("ravi@yahoo.com"), key=idp.stranger_key)
    assert await _refusal(YAHOO, token) == "bad-signature"


@pytest.mark.parametrize("alg", ["none", "HS256", "RS512"])
async def test_an_algorithm_outside_rs256_and_es256_is_refused_before_keys_are_read(
    idp: FakeIdP, alg: str
) -> None:
    token = idp.sign(idp.yahoo_claims("ravi@yahoo.com"), alg=alg, kid="rsa-1")
    assert await _refusal(YAHOO, token) == "algorithm-refused"
    assert idp.jwks_fetches == 0


async def test_a_tampered_payload_is_refused(idp: FakeIdP) -> None:
    header, _payload, signature = idp.sign(idp.yahoo_claims("ravi@yahoo.com")).split(".")
    forged = idp.sign(idp.yahoo_claims("someone-else@yahoo.com")).split(".")[1]
    assert await _refusal(YAHOO, f"{header}.{forged}.{signature}") == "bad-signature"


@pytest.mark.parametrize("token", ["", "a.b", "not.a.jwt", "x" * 50])
async def test_a_malformed_token_is_refused(idp: FakeIdP, token: str) -> None:
    assert await _refusal(YAHOO, token) == "malformed-token"


async def test_a_yahoo_token_from_another_issuer_is_refused(idp: FakeIdP) -> None:
    token = idp.sign(idp.yahoo_claims("ravi@yahoo.com", iss="https://login.yahoo.com"))
    assert await _refusal(YAHOO, token) == "wrong-issuer"


async def test_a_yahoo_token_for_another_app_is_refused(idp: FakeIdP) -> None:
    token = idp.sign(idp.yahoo_claims("ravi@yahoo.com", aud="another-apps-client-id"))
    assert await _refusal(YAHOO, token) == "wrong-audience"


async def test_several_audiences_need_azp_to_name_this_app(idp: FakeIdP) -> None:
    claims = idp.yahoo_claims("ravi@yahoo.com", aud=[YAHOO_CLIENT_ID, "other"])
    assert await _refusal(YAHOO, idp.sign(claims)) == "wrong-audience"
    claims["azp"] = YAHOO_CLIENT_ID
    assert (await _verify(YAHOO, idp.sign(claims)))["azp"] == YAHOO_CLIENT_ID


async def test_a_microsoft_issuer_must_name_the_tokens_own_tenant(idp: FakeIdP) -> None:
    claims = idp.microsoft_claims("m@contoso.com", tenant=WORK_TENANT, xms_edov=True)
    claims["iss"] = "https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0"
    assert await _refusal(MICROSOFT, idp.sign(claims)) == "wrong-issuer"


async def test_the_configured_microsoft_tenant_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    personal_only = FakeIdP().install(monkeypatch, microsoft_tenant="consumers")
    work_token = personal_only.sign(personal_only.microsoft_claims("m@contoso.com", tenant=WORK_TENANT))
    assert await _refusal(MICROSOFT, work_token) == "wrong-tenant"
    work_only = FakeIdP().install(monkeypatch, microsoft_tenant="organizations")
    assert (
        await _refusal(MICROSOFT, work_only.sign(work_only.microsoft_claims("m@outlook.com")))
        == "wrong-tenant"
    )


def test_a_tenant_named_by_domain_turns_microsoft_off(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeIdP().install(monkeypatch, microsoft_tenant="contoso.onmicrosoft.com")
    assert oidc_sign_in.provider(MICROSOFT) is None


async def test_an_expired_token_is_refused_and_a_minute_of_drift_is_not(idp: FakeIdP) -> None:
    claims = idp.yahoo_claims("ravi@yahoo.com")
    token = idp.sign(claims)
    assert await _verify(YAHOO, token, now=claims["exp"] + 30)
    assert await _refusal(YAHOO, token, now=claims["exp"] + 61) == "expired"


async def test_a_token_without_exp_is_refused(idp: FakeIdP) -> None:
    claims = idp.yahoo_claims("ravi@yahoo.com")
    del claims["exp"]
    assert await _refusal(YAHOO, idp.sign(claims)) == "expired"


async def test_a_token_from_the_future_is_refused(idp: FakeIdP) -> None:
    later = int(time.time()) + 600
    not_yet = idp.sign(idp.microsoft_claims("m@outlook.com", nbf=later))
    assert await _refusal(MICROSOFT, not_yet) == "not-yet-valid"
    issued_later = idp.sign(idp.yahoo_claims("ravi@yahoo.com", iat=later))
    assert await _refusal(YAHOO, issued_later) == "issued-in-the-future"


async def test_the_nonce_must_be_the_digest_of_the_raw_value_the_caller_holds(idp: FakeIdP) -> None:
    token = idp.sign(idp.yahoo_claims("ravi@yahoo.com"))
    assert await _refusal(YAHOO, token, raw_nonce="somebody-elses-raw-nonce-value") == "nonce-mismatch"
    digest_sent_as_raw = idp.yahoo_claims("x@yahoo.com")["nonce"]
    assert await _refusal(YAHOO, token, raw_nonce=digest_sent_as_raw) == "nonce-mismatch"
    claims = idp.yahoo_claims("ravi@yahoo.com")
    del claims["nonce"]
    assert await _refusal(YAHOO, idp.sign(claims)) == "nonce-mismatch"


def test_the_nonce_digest_is_rfc_7636_s256() -> None:
    raw = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert oidc_sign_in.nonce_digest(raw) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def _email(name: str, claims: dict) -> str:
    p = oidc_sign_in.provider(name)
    assert p is not None
    return oidc_sign_in.verified_email(p, claims)


def test_a_personal_microsoft_address_is_verified_and_only_lower_cased(idp: FakeIdP) -> None:
    claims = idp.microsoft_claims("Meera.Iyer+Field@Gmail.com")
    assert _email(MICROSOFT, claims) == "meera.iyer+field@gmail.com"


def test_a_work_account_address_needs_xms_edov(idp: FakeIdP) -> None:
    with pytest.raises(EmailNotVerified):
        _email(MICROSOFT, idp.microsoft_claims("ceo@contoso.com", tenant=WORK_TENANT))
    with pytest.raises(EmailNotVerified):
        _email(MICROSOFT, idp.microsoft_claims("ceo@contoso.com", tenant=WORK_TENANT, xms_edov=False))
    verified = idp.microsoft_claims("ceo@contoso.com", tenant=WORK_TENANT, xms_edov=True)
    assert _email(MICROSOFT, verified) == "ceo@contoso.com"


@pytest.mark.parametrize("flag", [False, None, "false", 0])
def test_a_yahoo_address_needs_email_verified(idp: FakeIdP, flag: object) -> None:
    with pytest.raises(EmailNotVerified):
        _email(YAHOO, idp.yahoo_claims("ravi@yahoo.com", email_verified=flag))


def test_no_email_at_all_is_unverified(idp: FakeIdP) -> None:
    claims = idp.yahoo_claims("ravi@yahoo.com")
    del claims["email"]
    with pytest.raises(EmailNotVerified):
        _email(YAHOO, claims)


async def test_prove_redeems_with_the_secret_and_the_verifier_then_verifies(idp: FakeIdP) -> None:
    idp.issue(idp.sign(idp.yahoo_claims("Ravi@Yahoo.com")))
    proved = await oidc_sign_in.prove(
        YAHOO, code="c0de", code_verifier=VERIFIER, redirect_uri=REDIRECT_URI, raw_nonce=RAW_NONCE
    )
    assert (proved.provider, proved.email, proved.name) == ("YAHOO", "ravi@yahoo.com", "Ravi Kumar")
    url, form = idp.redemptions[-1]
    assert url == "https://api.login.yahoo.com/oauth2/get_token"
    assert form == {
        "grant_type": "authorization_code",
        "code": "c0de",
        "redirect_uri": REDIRECT_URI,
        "client_id": YAHOO_CLIENT_ID,
        "client_secret": YAHOO_SECRET,
        "code_verifier": VERIFIER,
    }


async def test_microsoft_redemption_goes_to_the_configured_tenant(idp: FakeIdP) -> None:
    idp.issue(idp.sign(idp.microsoft_claims("m@outlook.com")))
    await oidc_sign_in.prove(
        MICROSOFT, code="c", code_verifier=VERIFIER, redirect_uri=REDIRECT_URI, raw_nonce=RAW_NONCE
    )
    url, form = idp.redemptions[-1]
    assert url == "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    assert (form["client_id"], form["scope"]) == (MICROSOFT_CLIENT_ID, "openid email profile")


async def test_a_refused_redemption_logs_no_credential(
    idp: FakeIdP, caplog: pytest.LogCaptureFixture
) -> None:
    idp.next_answer = (400, {"error": "invalid_grant", "error_description": "code c0de-secret was used"})
    with caplog.at_level(logging.INFO), pytest.raises(SignInRefused) as caught:
        await oidc_sign_in.prove(
            YAHOO, code="c0de-secret", code_verifier=VERIFIER, redirect_uri=REDIRECT_URI, raw_nonce=RAW_NONCE
        )
    assert caught.value.reason == "redemption-refused"
    logged = " ".join(f"{record.getMessage()} {record.__dict__}" for record in caplog.records)
    assert "invalid_grant" in logged
    for secret in ("c0de-secret", VERIFIER, RAW_NONCE, YAHOO_SECRET, "was used"):
        assert secret not in logged


async def test_yahoo_without_its_secret_is_off_and_proves_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeIdP().install(monkeypatch, yahoo_client_secret="")
    assert oidc_sign_in.provider(YAHOO) is None
    assert oidc_sign_in.client_id_if_enabled(YAHOO) is None
    with pytest.raises(SignInRefused):
        await oidc_sign_in.prove(
            YAHOO, code="c", code_verifier=VERIFIER, redirect_uri=REDIRECT_URI, raw_nonce=RAW_NONCE
        )


@pytest.mark.parametrize(
    ("uri", "accepted"),
    [
        ("https://kalavigyan.example.org/login/callback", True),
        ("http://kalavigyan.example.org/login/callback", False),
        ("https://kalavigyan.example.org/login/callback/", False),
        ("https://kalavigyan.example.org/login/callback?next=/", False),
        ("https://elsewhere.example.org/login/callback", False),
        ("", False),
    ],
)
def test_only_the_public_web_callback_is_a_redirect_uri(idp: FakeIdP, uri: str, accepted: bool) -> None:
    assert oidc_sign_in.acceptable_redirect_uri(uri) is accepted


def test_the_login_body_takes_exactly_one_credential() -> None:
    assert LoginRequest(**login_body("YAHOO")).has_oidc_code
    with pytest.raises(ValidationError):
        LoginRequest(**login_body("YAHOO"), googleIdToken="t")
    with pytest.raises(ValidationError):
        LoginRequest(**{**login_body("YAHOO"), "oidcNonce": None})
    with pytest.raises(ValidationError):
        LoginRequest(**login_body("GITHUB"))
    with pytest.raises(ValidationError):
        LoginRequest(**{**login_body("YAHOO"), "oidcCodeVerifier": "short"})


async def test_config_hides_both_providers_without_keys(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    unset = {"yahoo_client_id": None, "yahoo_client_secret": None, "microsoft_client_id": None}
    monkeypatch.setattr(oidc_sign_in, "get_settings", lambda: fake_settings(**unset))
    body = (await client.get("/api/auth/config")).json()
    assert (body["yahooEnabled"], body["yahooClientId"]) == (False, None)
    assert (body["microsoftEnabled"], body["microsoftClientId"]) == (False, None)


async def test_config_reports_yahoo_when_its_id_and_secret_are_set(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(oidc_sign_in, "get_settings", lambda: fake_settings(microsoft_client_secret=" "))
    body = (await client.get("/api/auth/config")).json()
    assert (body["yahooEnabled"], body["yahooClientId"]) == (True, YAHOO_CLIENT_ID)
    assert (body["microsoftEnabled"], body["microsoftClientId"]) == (False, None)


async def test_no_nonce_and_no_sign_in_for_a_provider_that_is_off(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(oidc_sign_in, "get_settings", lambda: fake_settings(yahoo_client_id=""))
    nonce = await client.post("/api/auth/oidc/nonce", json={"provider": "YAHOO"})
    assert nonce.status_code == 404
    login = await client.post("/api/auth/login", json=login_body("YAHOO"))
    assert login.status_code == 400
    assert (
        login.json()["detail"]
        == "Yahoo sign-in isn't available right now. Sign in with your email and password."
    )


async def test_the_nonce_route_names_only_the_two_providers(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/auth/oidc/nonce", json={"provider": "GITHUB"})
    assert response.status_code == 422


def test_the_migration_downgrade_restores_the_initial_values() -> None:
    later = ast.parse((MIGRATIONS / "0010_oidc_sign_in.py").read_text(encoding="utf-8"))
    initial = initial_enum_list()
    assert module_constant(later, "AUTH_PROVIDERS_BEFORE") == initial["AuthProvider"] == ("LOCAL", "GOOGLE")
    assert module_constant(later, "AUTH_NONCE_PURPOSES_BEFORE") == initial["AuthNoncePurpose"]
    assert enum_additions()["AuthProvider"] == ("MICROSOFT", "YAHOO")
    assert dict(module_constant(later, "ENUM_ADDITIONS"))["AuthNoncePurpose"] == ("OIDC_SIGN_IN",)
