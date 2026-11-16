import base64
import hashlib
import hmac
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.auth_nonces import consume_nonce
from app.services.signed_tokens import TokenRefused as SignInRefused, check_signature, split_token

logger = logging.getLogger(__name__)

MICROSOFT = "MICROSOFT"
YAHOO = "YAHOO"
PROVIDERS = (MICROSOFT, YAHOO)
NONCE_PURPOSE = "OIDC_SIGN_IN"
CALLBACK_PATH = "/login/callback"

MICROSOFT_CONSUMER_TENANT = "9188040d-6c67-4c5b-b112-36a304b66dad"
MICROSOFT_LOGIN_HOST = "https://login.microsoftonline.com"
MICROSOFT_TENANT_KEYWORDS = ("common", "organizations", "consumers")

YAHOO_ISSUER = "https://api.login.yahoo.com"
YAHOO_TOKEN_ENDPOINT = "https://api.login.yahoo.com/oauth2/get_token"
YAHOO_JWKS_URI = "https://api.login.yahoo.com/openid/v1/certs"

CLOCK_LEEWAY_SECONDS = 60
HTTP_TIMEOUT_SECONDS = 10

_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class EmailNotVerified(SignInRefused):
    pass


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    client_id: str
    client_secret: str
    token_endpoint: str
    jwks_uri: str
    tenant: str | None = None
    scope: str = "openid email profile"


@dataclass(frozen=True)
class CodeGrant:
    provider: str
    code: str
    code_verifier: str
    redirect_uri: str
    raw_nonce: str


@dataclass(frozen=True)
class ProvedIdentity:
    provider: str
    email: str
    name: str | None
    issued_at: float | None = None


def label_of(name: str) -> str:
    return {MICROSOFT: "Microsoft", YAHOO: "Yahoo"}.get(name, name.title())


def microsoft_tenant(raw: str | None) -> str | None:
    value = (raw or "common").strip().lower()
    if value in MICROSOFT_TENANT_KEYWORDS or _GUID.match(value):
        return value
    return None


def _microsoft() -> Provider | None:
    settings = get_settings()
    client_id = (settings.microsoft_client_id or "").strip()
    secret = (settings.microsoft_client_secret or "").strip()
    if not client_id or not secret:
        return None
    tenant = microsoft_tenant(settings.microsoft_tenant)
    if tenant is None:
        logger.error("oidc: MICROSOFT_TENANT is not a tenant keyword or ID, so Microsoft sign-in is off")
        return None
    return Provider(
        name=MICROSOFT,
        label="Microsoft",
        client_id=client_id,
        client_secret=secret,
        token_endpoint=f"{MICROSOFT_LOGIN_HOST}/{tenant}/oauth2/v2.0/token",
        jwks_uri=f"{MICROSOFT_LOGIN_HOST}/{tenant}/discovery/v2.0/keys",
        tenant=tenant,
    )


def _yahoo() -> Provider | None:
    settings = get_settings()
    client_id = (settings.yahoo_client_id or "").strip()
    secret = (settings.yahoo_client_secret or "").strip()
    if not client_id or not secret:
        return None
    return Provider(
        name=YAHOO,
        label="Yahoo",
        client_id=client_id,
        client_secret=secret,
        token_endpoint=YAHOO_TOKEN_ENDPOINT,
        jwks_uri=YAHOO_JWKS_URI,
    )


def provider(name: str) -> Provider | None:
    if name == MICROSOFT:
        return _microsoft()
    if name == YAHOO:
        return _yahoo()
    return None


def client_id_if_enabled(name: str) -> str | None:
    configured = provider(name)
    return configured.client_id if configured is not None else None


def nonce_digest(raw_nonce: str) -> str:
    digest = hashlib.sha256(raw_nonce.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def callback_uri() -> str:
    return get_settings().public_web_url.strip().rstrip("/") + CALLBACK_PATH


def acceptable_redirect_uri(uri: str) -> bool:
    return hmac.compare_digest(uri.encode("utf-8"), callback_uri().encode("utf-8"))


async def _post_form(url: str, data: dict[str, str]) -> tuple[int, Any]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        response = await client.post(url, data=data, headers={"Accept": "application/json"})
    try:
        body = response.json()
    except ValueError:
        body = None
    return response.status_code, body


def _redemption_form(p: Provider, *, code: str, code_verifier: str, redirect_uri: str) -> dict[str, str]:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": p.client_id,
        "client_secret": p.client_secret,
        "code_verifier": code_verifier,
    }
    if p.name == MICROSOFT:
        data["scope"] = p.scope
    return data


def _error_code(body: Any) -> str:
    error = body.get("error") if isinstance(body, dict) else None
    return error if isinstance(error, str) and error.isidentifier() else "no error code"


async def redeem_code(p: Provider, *, code: str, code_verifier: str, redirect_uri: str) -> str:
    data = _redemption_form(p, code=code, code_verifier=code_verifier, redirect_uri=redirect_uri)
    try:
        status_code, body = await _post_form(p.token_endpoint, data)
    except httpx.HTTPError as exc:
        logger.warning(
            "oidc: redemption did not complete", extra={"provider": p.name, "error": type(exc).__name__}
        )
        raise SignInRefused("redemption-unreachable") from exc
    if status_code != 200 or not isinstance(body, dict):
        logger.info(
            "oidc: the provider refused the redemption",
            extra={"provider": p.name, "status": status_code, "error": _error_code(body)},
        )
        raise SignInRefused("redemption-refused")
    id_token = body.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        logger.info("oidc: the redemption carried no ID token", extra={"provider": p.name})
        raise SignInRefused("no-id-token")
    return id_token


def _expected_issuer(p: Provider, claims: dict[str, Any]) -> str:
    if p.name == YAHOO:
        return YAHOO_ISSUER
    tid = claims.get("tid")
    if not isinstance(tid, str) or not _GUID.match(tid.lower()):
        raise SignInRefused("no-tenant")
    tid = tid.lower()
    if p.tenant == "consumers" and tid != MICROSOFT_CONSUMER_TENANT:
        raise SignInRefused("wrong-tenant")
    if p.tenant == "organizations" and tid == MICROSOFT_CONSUMER_TENANT:
        raise SignInRefused("wrong-tenant")
    if p.tenant not in MICROSOFT_TENANT_KEYWORDS and tid != p.tenant:
        raise SignInRefused("wrong-tenant")
    return f"{MICROSOFT_LOGIN_HOST}/{tid}/v2.0"


def _check_issuer_and_audience(p: Provider, claims: dict[str, Any]) -> None:
    if claims.get("iss") != _expected_issuer(p, claims):
        raise SignInRefused("wrong-issuer")
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if p.client_id not in audiences:
        raise SignInRefused("wrong-audience")
    if len(audiences) > 1 and claims.get("azp") != p.client_id:
        raise SignInRefused("wrong-audience")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _check_lifetime(claims: dict[str, Any], moment: float) -> None:
    expires = _number(claims.get("exp"))
    if expires is None or expires <= moment - CLOCK_LEEWAY_SECONDS:
        raise SignInRefused("expired")
    not_before = _number(claims.get("nbf"))
    if not_before is not None and not_before > moment + CLOCK_LEEWAY_SECONDS:
        raise SignInRefused("not-yet-valid")
    issued = _number(claims.get("iat"))
    if issued is not None and issued > moment + CLOCK_LEEWAY_SECONDS:
        raise SignInRefused("issued-in-the-future")


def _check_nonce(claims: dict[str, Any], raw_nonce: str) -> None:
    nonce = claims.get("nonce")
    expected = nonce_digest(raw_nonce).encode("utf-8")
    if not isinstance(nonce, str) or not hmac.compare_digest(nonce.encode("utf-8"), expected):
        raise SignInRefused("nonce-mismatch")


async def verify_id_token(
    p: Provider, token: str, *, raw_nonce: str, now: float | None = None
) -> dict[str, Any]:
    signed = split_token(token)
    await check_signature(signed, p.jwks_uri)
    _check_issuer_and_audience(p, signed.claims)
    _check_lifetime(signed.claims, time.time() if now is None else now)
    _check_nonce(signed.claims, raw_nonce)
    return signed.claims


def _truthy(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() in ("true", "1"))


def verified_email(p: Provider, claims: dict[str, Any]) -> str:
    email = claims.get("email")
    if not isinstance(email, str) or "@" not in email.strip():
        raise EmailNotVerified("no-email")
    if p.name == YAHOO:
        verified = _truthy(claims.get("email_verified"))
    else:
        tid = str(claims.get("tid") or "").lower()
        verified = tid == MICROSOFT_CONSUMER_TENANT or _truthy(claims.get("xms_edov"))
    if not verified:
        raise EmailNotVerified("email-not-verified")
    return email.strip().lower()


def display_name(claims: dict[str, Any]) -> str | None:
    name = claims.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()[:200]
    given = claims.get("given_name")
    family = claims.get("family_name")
    joined = " ".join(part.strip() for part in (given, family) if isinstance(part, str) and part.strip())
    return joined[:200] or None


async def prove(
    name: str, *, code: str, code_verifier: str, redirect_uri: str, raw_nonce: str
) -> ProvedIdentity:
    p = provider(name)
    if p is None:
        raise SignInRefused("not-configured")
    token = await redeem_code(p, code=code, code_verifier=code_verifier, redirect_uri=redirect_uri)
    claims = await verify_id_token(p, token, raw_nonce=raw_nonce)
    return ProvedIdentity(
        provider=p.name,
        email=verified_email(p, claims),
        name=display_name(claims),
        issued_at=_number(claims.get("iat")),
    )


async def prove_once(
    session: AsyncSession, grant: CodeGrant, *, purpose: str, user_id: Any = None
) -> ProvedIdentity:
    if provider(grant.provider) is None:
        raise SignInRefused("not-configured")
    if not acceptable_redirect_uri(grant.redirect_uri):
        raise SignInRefused("redirect-uri-refused")
    spent = await consume_nonce(session, grant.raw_nonce, purpose=purpose, user_id=user_id)
    await session.commit()
    if not spent:
        raise SignInRefused("nonce-unknown-or-spent")
    return await prove(
        grant.provider,
        code=grant.code,
        code_verifier=grant.code_verifier,
        redirect_uri=grant.redirect_uri,
        raw_nonce=grant.raw_nonce,
    )
