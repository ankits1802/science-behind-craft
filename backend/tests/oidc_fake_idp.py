import base64
import hashlib
import json
import time
from types import SimpleNamespace
from typing import Any

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from app.services import oidc_sign_in, signed_tokens

MICROSOFT_CLIENT_ID = "00000000-aaaa-bbbb-cccc-000000000001"
YAHOO_CLIENT_ID = "dj0yJmk9ZmFrZS15YWhvby1jbGllbnQ"
YAHOO_SECRET = "yahoo-secret-value"
WORK_TENANT = "72f988bf-86f1-41af-91ab-2d7cd011db47"
PERSONAL_TENANT = "9188040d-6c67-4c5b-b112-36a304b66dad"
RAW_NONCE = "a-raw-nonce-only-the-client-holds-0123456789"
VERIFIER = "v" * 64
WEB_ORIGIN = "https://kalavigyan.example.org"
REDIRECT_URI = "https://kalavigyan.example.org/login/callback"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _int_b64(value: int) -> str:
    return _b64(value.to_bytes((value.bit_length() + 7) // 8, "big"))


def sha256_b64url(text: str) -> str:
    return _b64(hashlib.sha256(text.encode("utf-8")).digest())


def fake_settings(**overrides: Any) -> SimpleNamespace:
    values = {
        "microsoft_client_id": MICROSOFT_CLIENT_ID,
        "microsoft_client_secret": "microsoft-secret-value",
        "microsoft_tenant": "common",
        "yahoo_client_id": YAHOO_CLIENT_ID,
        "yahoo_client_secret": YAHOO_SECRET,
        "public_web_url": WEB_ORIGIN + "/",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _public_jwks(rsa_key: rsa.RSAPrivateKey, ec_key: ec.EllipticCurvePrivateKey) -> dict[str, Any]:
    rsa_public = rsa_key.public_key().public_numbers()
    ec_public = ec_key.public_key().public_numbers()
    rsa_jwk = {"kty": "RSA", "kid": "rsa-1", "use": "sig", "alg": "RS256"}
    rsa_jwk |= {"n": _int_b64(rsa_public.n), "e": _int_b64(rsa_public.e)}
    ec_jwk = {"kty": "EC", "kid": "ec-1", "use": "sig", "crv": "P-256"}
    ec_jwk |= {"x": _b64(ec_public.x.to_bytes(32, "big")), "y": _b64(ec_public.y.to_bytes(32, "big"))}
    return {"keys": [rsa_jwk, ec_jwk]}


class FakeIdP:
    def __init__(self) -> None:
        self.rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.ec_key = ec.generate_private_key(ec.SECP256R1())
        self.stranger_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.jwks = _public_jwks(self.rsa_key, self.ec_key)
        self.jwks_fetches = 0
        self.redemptions: list[tuple[str, dict[str, str]]] = []
        self.next_answer: tuple[int, Any] = (400, {"error": "invalid_grant"})

    def _signature(self, signing_input: str, alg: str, key: Any) -> bytes:
        if alg == "RS256":
            signer = key or self.rsa_key
            return signer.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
        if alg == "ES256":
            der = (key or self.ec_key).sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
            r, s = decode_dss_signature(der)
            return r.to_bytes(32, "big") + s.to_bytes(32, "big")
        return b""

    def sign(
        self, claims: dict[str, Any], *, alg: str = "RS256", kid: str | None = None, key: Any = None
    ) -> str:
        header: dict[str, Any] = {"alg": alg, "typ": "JWT"}
        if kid is not None or alg in ("RS256", "ES256"):
            header["kid"] = kid if kid is not None else ("ec-1" if alg == "ES256" else "rsa-1")
        signing_input = f"{_b64(json.dumps(header).encode())}.{_b64(json.dumps(claims).encode())}"
        return f"{signing_input}.{_b64(self._signature(signing_input, alg, key))}"

    @staticmethod
    def microsoft_claims(
        email: str, *, tenant: str = PERSONAL_TENANT, raw_nonce: str = RAW_NONCE, **extra: Any
    ) -> dict[str, Any]:
        now = int(time.time())
        claims = {
            "iss": f"https://login.microsoftonline.com/{tenant}/v2.0",
            "aud": MICROSOFT_CLIENT_ID,
            "tid": tenant,
            "sub": "pairwise-subject",
            "email": email,
            "name": "Meera Iyer",
            "iat": now,
            "nbf": now,
            "exp": now + 3600,
            "nonce": sha256_b64url(raw_nonce),
        }
        return claims | extra

    @staticmethod
    def yahoo_claims(email: str, *, raw_nonce: str = RAW_NONCE, **extra: Any) -> dict[str, Any]:
        now = int(time.time())
        claims = {
            "iss": "https://api.login.yahoo.com",
            "aud": YAHOO_CLIENT_ID,
            "sub": "yahoo-subject",
            "email": email,
            "email_verified": True,
            "name": "Ravi Kumar",
            "iat": now,
            "exp": now + 3600,
            "nonce": sha256_b64url(raw_nonce),
        }
        return claims | extra

    def issue(self, token: str) -> None:
        self.next_answer = (200, {"id_token": token, "token_type": "Bearer", "access_token": "at"})

    async def post_form(self, url: str, data: dict[str, str]) -> tuple[int, Any]:
        self.redemptions.append((url, dict(data)))
        return self.next_answer

    async def get_json(self, url: str) -> Any:
        self.jwks_fetches += 1
        return self.jwks

    def install(self, monkeypatch: pytest.MonkeyPatch, **setting_overrides: Any) -> FakeIdP:
        signed_tokens.forget_cached_keys()
        monkeypatch.setattr(oidc_sign_in, "_post_form", self.post_form)
        monkeypatch.setattr(signed_tokens, "_get_json", self.get_json)
        monkeypatch.setattr(oidc_sign_in, "get_settings", lambda: fake_settings(**setting_overrides))
        return self


def login_body(provider: str, *, code: str = "the-code", raw_nonce: str = RAW_NONCE) -> dict[str, str]:
    return {
        "oidcProvider": provider,
        "oidcCode": code,
        "oidcCodeVerifier": VERIFIER,
        "oidcRedirectUri": REDIRECT_URI,
        "oidcNonce": raw_nonce,
    }
