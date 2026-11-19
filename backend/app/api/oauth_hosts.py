from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import HTTPException, status

from app.core.config import Settings, get_settings
from app.core.deps import API_PREFIX
from app.core.errors import NotConfigured
from app.research.oauth_metadata import OAuthEndpoints
from app.research.oauth_rules import is_loopback_host

__all__ = [
    "AUTHORIZATION_SERVER_PATH",
    "AUTHORIZE_PAGE",
    "MCP_RESOURCE_PATH",
    "MCP_ROUTE",
    "OAUTH_ROUTE",
    "PROTECTED_RESOURCE_PATH",
    "REGISTER_ROUTE",
    "REVOKE_ROUTE",
    "TOKEN_ROUTE",
    "configured_endpoints",
    "endpoints_or_none",
    "oauth_endpoints",
]

MCP_ROUTE = "/mcp"
OAUTH_ROUTE = "/oauth"
TOKEN_ROUTE = "/token"
REGISTER_ROUTE = "/register"
REVOKE_ROUTE = "/revoke"
AUTHORIZE_PAGE = "/oauth/authorize"
PROTECTED_RESOURCE_PATH = "/.well-known/oauth-protected-resource"
AUTHORIZATION_SERVER_PATH = "/.well-known/oauth-authorization-server"
MCP_RESOURCE_PATH = f"{API_PREFIX}{MCP_ROUTE}"
NOT_CONFIGURED_DETAIL = "Agents cannot sign in to KalaVigyan right now."


def oauth_endpoints(settings: Settings) -> OAuthEndpoints:
    api = _origin("PUBLIC_API_URL", settings.public_api_url)
    web = _origin("PUBLIC_WEB_URL", settings.public_web_url)
    oauth = f"{api}{API_PREFIX}{OAUTH_ROUTE}"
    return OAuthEndpoints(
        issuer=api,
        resource=f"{api}{MCP_RESOURCE_PATH}",
        resource_metadata=f"{api}{PROTECTED_RESOURCE_PATH}{MCP_RESOURCE_PATH}",
        authorization=f"{web}{AUTHORIZE_PAGE}",
        token=f"{oauth}{TOKEN_ROUTE}",
        registration=f"{oauth}{REGISTER_ROUTE}",
        revocation=f"{oauth}{REVOKE_ROUTE}",
    )


def configured_endpoints() -> OAuthEndpoints:
    try:
        return oauth_endpoints(get_settings())
    except NotConfigured as missing:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NOT_CONFIGURED_DETAIL) from missing


def endpoints_or_none() -> OAuthEndpoints | None:
    try:
        return oauth_endpoints(get_settings())
    except NotConfigured:
        return None


def _origin(name: str, value: str | None) -> str:
    origin = (value or "").strip().rstrip("/")
    parts = urlsplit(origin)
    secure = parts.scheme == "https" or (parts.scheme == "http" and is_loopback_host(parts.hostname))
    if not parts.hostname or not secure or parts.path or parts.query or parts.fragment:
        raise NotConfigured(
            name, f"{name} must be an https origin, or http on this machine, to sign agents in"
        )
    return origin
