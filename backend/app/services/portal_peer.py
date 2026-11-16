from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import ExternalFailure, NotConfigured, Refused
from app.services.portal_craft_feed import DESIGNER, FIELD_REPOSITORY, PortalCraftFeed, parse_feed

__all__ = [
    "CRAFT_FEED_PATH",
    "FEED_MAX_BYTES",
    "FEED_TIMEOUT_SECONDS",
    "MIN_TOKEN_LENGTH",
    "NONCE_HEADER",
    "PEER_PREFIX",
    "REQUESTED_BY",
    "REQUESTED_BY_HEADER",
    "SIGNATURE_HEADER",
    "PortalPeer",
    "peer_for",
    "peer_signature",
]

logger = logging.getLogger(__name__)

PEER_PREFIX = "/cross-portal/peer"
CRAFT_FEED_PATH = "/crafts"
SIGNATURE_HEADER = "X-Cross-Portal-Signature"
NONCE_HEADER = "X-Cross-Portal-Nonce"
REQUESTED_BY_HEADER = "X-Cross-Portal-Requested-By"
REQUESTED_BY = "kalavigyan-craft-sync"
MIN_TOKEN_LENGTH = 32
FEED_TIMEOUT_SECONDS = 30.0
FEED_MAX_BYTES = 20 * 1024 * 1024

BASE_URL_SETTINGS = {
    DESIGNER: ("designer_portal_api_url", "DESIGNER_PORTAL_API_URL"),
    FIELD_REPOSITORY: ("field_repository_api_url", "FIELD_REPOSITORY_API_URL"),
}

FAILURE_BY_STATUS = {401: "auth", 403: "auth", 404: "not_found", 429: "rate_limit"}


def peer_signature(token: str, body: bytes, *, method: str, path: str, nonce: str) -> str:
    head = "\n".join((method.upper(), path, nonce, "")).encode("utf-8")
    return hmac.new(token.strip().encode("utf-8"), head + body, hashlib.sha256).hexdigest()


class PortalPeer:
    def __init__(
        self,
        *,
        portal: str,
        base_url: str,
        token: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.portal = portal
        self._base_url = base_url.rstrip("/")
        self._token = token.strip()
        self._transport = transport

    async def craft_feed(self) -> PortalCraftFeed:
        path = f"{PEER_PREFIX}{CRAFT_FEED_PATH}"
        nonce = secrets.token_hex(16)
        response = await self._get(path, nonce)
        self._refuse_failure(response)
        body = response.content
        if len(body) > FEED_MAX_BYTES:
            raise ExternalFailure(
                f"{self.portal} craft feed is {len(body)} bytes, over {FEED_MAX_BYTES}", service=self.portal
            )
        signature = response.headers.get(SIGNATURE_HEADER) or ""
        expected = peer_signature(self._token, body, method="GET", path=path, nonce=nonce)
        if not hmac.compare_digest(expected, signature):
            raise Refused(
                "unsigned_answer", f"{self.portal} craft feed is not signed with the cross-portal token"
            )
        return parse_feed(_json(body, self.portal), portal=self.portal)

    async def _get(self, path: str, nonce: str) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            NONCE_HEADER: nonce,
            REQUESTED_BY_HEADER: REQUESTED_BY,
        }
        try:
            async with httpx.AsyncClient(timeout=FEED_TIMEOUT_SECONDS, transport=self._transport) as client:
                return await client.get(f"{self._base_url}{path}", headers=headers)
        except httpx.HTTPError as error:
            logger.warning("%s craft feed could not be reached: %s", self.portal, type(error).__name__)
            raise ExternalFailure(
                f"{self.portal} craft feed could not be reached ({type(error).__name__})",
                kind="unavailable",
                retryable=True,
                service=self.portal,
            ) from None

    def _refuse_failure(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        kind = FAILURE_BY_STATUS.get(
            response.status_code, "unavailable" if response.status_code >= 500 else "error"
        )
        raise ExternalFailure(
            f"{self.portal} craft feed answered {response.status_code}",
            kind=kind,
            retryable=kind in ("rate_limit", "unavailable"),
            status=response.status_code,
            service=self.portal,
        )


def peer_for(
    settings: Settings, portal: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> PortalPeer:
    attribute, env_name = BASE_URL_SETTINGS[portal]
    base_url = (getattr(settings, attribute) or "").strip()
    if not base_url.startswith("https://"):
        raise NotConfigured(env_name, f"{env_name} must be the portal's https API address")
    token = (settings.cross_portal_token or "").strip()
    if len(token) < MIN_TOKEN_LENGTH:
        raise NotConfigured(
            "CROSS_PORTAL_TOKEN", f"CROSS_PORTAL_TOKEN must be at least {MIN_TOKEN_LENGTH} characters"
        )
    return PortalPeer(portal=portal, base_url=base_url, token=token, transport=transport)


def _json(body: bytes, portal: str) -> Any:
    try:
        return json.loads(body.decode("utf-8"))
    except ValueError:
        raise ExternalFailure(f"{portal} craft feed is not UTF-8 JSON", service=portal) from None
