import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.auth_nonces import consume_nonce

logger = logging.getLogger(__name__)

GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


class GoogleSignInRefused(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def client_id_if_enabled() -> str | None:
    return (get_settings().google_client_id or "").strip() or None


def google_enabled() -> bool:
    return client_id_if_enabled() is not None


def _verify_sync(token: str, client_id: str) -> dict[str, Any]:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    return google_id_token.verify_oauth2_token(token, google_requests.Request(), client_id)


def check_claims(claims: dict[str, Any], client_id: str, now: float | None = None) -> str | None:
    if claims.get("aud") != client_id:
        return "audience"
    if claims.get("iss") not in GOOGLE_ISSUERS:
        return "issuer"
    exp = claims.get("exp")
    moment = datetime.now(UTC).timestamp() if now is None else now
    if not isinstance(exp, int | float) or exp <= moment:
        return "expired"
    if not claims.get("email") or claims.get("email_verified") is not True:
        return "email_unverified"
    if not isinstance(claims.get("nonce"), str) or not claims["nonce"]:
        return "nonce_missing"
    return None


async def verify_id_token(token: str) -> dict[str, Any]:
    client_id = (get_settings().google_client_id or "").strip()
    if not client_id:
        raise GoogleSignInRefused("not_configured")
    try:
        claims = await asyncio.to_thread(_verify_sync, token, client_id)
    except ValueError as exc:
        logger.info("google id token did not verify", extra={"error": type(exc).__name__})
        raise GoogleSignInRefused("invalid") from exc
    problem = check_claims(claims, client_id)
    if problem:
        raise GoogleSignInRefused(problem)
    return claims


async def verify_with_nonce(
    session: AsyncSession, token: str, *, purpose: str = "GOOGLE_SIGN_IN", user_id: Any = None
) -> dict[str, Any]:
    claims = await verify_id_token(token)
    if not await consume_nonce(session, claims["nonce"], purpose=purpose, user_id=user_id):
        raise GoogleSignInRefused("nonce_reused_or_unknown")
    return claims
