from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.deps import API_PREFIX

from .oauth_hosts import (
    AUTHORIZATION_SERVER_PATH,
    MCP_RESOURCE_PATH,
    OAUTH_ROUTE,
    PROTECTED_RESOURCE_PATH,
    REGISTER_ROUTE,
    REVOKE_ROUTE,
    TOKEN_ROUTE,
)

__all__ = [
    "ALLOWED_HEADERS",
    "EXPOSED_HEADERS",
    "OPEN_PATHS",
    "OpenCorsMiddleware",
    "is_open_path",
    "is_web_origin",
]

OAUTH_PREFIX = f"{API_PREFIX}{OAUTH_ROUTE}"
OPEN_PATHS = frozenset(
    {
        MCP_RESOURCE_PATH,
        PROTECTED_RESOURCE_PATH,
        f"{PROTECTED_RESOURCE_PATH}{MCP_RESOURCE_PATH}",
        AUTHORIZATION_SERVER_PATH,
        f"{OAUTH_PREFIX}{REGISTER_ROUTE}",
        f"{OAUTH_PREFIX}{TOKEN_ROUTE}",
        f"{OAUTH_PREFIX}{REVOKE_ROUTE}",
    }
)
ALLOWED_METHODS = "GET, POST, OPTIONS"
ALLOWED_HEADERS = (
    "Authorization, Content-Type, Accept, MCP-Protocol-Version, Mcp-Method, Mcp-Name, Mcp-Session-Id, "
    "Last-Event-ID"
)
EXPOSED_HEADERS = "WWW-Authenticate, Retry-After, MCP-Protocol-Version, Mcp-Session-Id"
PREFLIGHT_MAX_AGE = "600"
ANY_ORIGIN = "*"
CREDENTIALS_HEADER = "access-control-allow-credentials"
PREFLIGHT_HEADERS: Mapping[str, str] = MappingProxyType(
    {
        "Access-Control-Allow-Origin": ANY_ORIGIN,
        "Access-Control-Allow-Methods": ALLOWED_METHODS,
        "Access-Control-Allow-Headers": ALLOWED_HEADERS,
        "Access-Control-Max-Age": PREFLIGHT_MAX_AGE,
    }
)


def is_open_path(path: str) -> bool:
    return (path.rstrip("/") or "/") in OPEN_PATHS


def is_web_origin(origin: str) -> bool:
    try:
        parts = urlsplit(origin.strip())
        host = parts.hostname
    except ValueError:
        return False
    if not parts.scheme or not host or parts.username is not None:
        return False
    return not (parts.path or parts.query or parts.fragment)


class OpenCorsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not is_open_path(str(scope.get("path") or "")):
            await self.app(scope, receive, send)
            return
        if scope["method"] == "OPTIONS" and "access-control-request-method" in Headers(scope=scope):
            preflight = Response(status_code=204, headers=dict(PREFLIGHT_HEADERS))
            await preflight(scope, receive, send)
            return

        async def send_open(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if CREDENTIALS_HEADER in headers:
                    del headers[CREDENTIALS_HEADER]
                headers["Access-Control-Allow-Origin"] = ANY_ORIGIN
                headers["Access-Control-Expose-Headers"] = EXPOSED_HEADERS
            await send(message)

        await self.app(scope, receive, send_open)
