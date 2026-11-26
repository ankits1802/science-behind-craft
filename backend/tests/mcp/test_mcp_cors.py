from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.mcp_cors import is_open_path, is_web_origin
from app.api.routes.mcp import mcp_enabled
from app.core.db import get_session
from app.main import create_app

BROWSER_CLIENT = "https://inspector.example"
INITIALIZE = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}}
OPEN = (
    "/api/mcp",
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-protected-resource/api/mcp",
    "/.well-known/oauth-authorization-server",
    "/api/oauth/register",
    "/api/oauth/token",
    "/api/oauth/revoke",
)


async def no_session() -> AsyncIterator[Any]:
    yield None


def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = no_session
    app.dependency_overrides[mcp_enabled] = lambda: None
    return TestClient(app)


def preflight(path: str, origin: str = BROWSER_CLIENT) -> Any:
    asked = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    return client().options(path, headers={"Origin": origin, **asked})


@pytest.mark.parametrize("path", OPEN)
def test_every_endpoint_an_agent_calls_answers_a_preflight_from_any_origin_without_credentials(
    path: str,
) -> None:
    answered = preflight(path)
    assert answered.status_code == 204
    assert answered.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in answered.headers
    allowed = {name.strip().lower() for name in answered.headers["access-control-allow-headers"].split(",")}
    assert {"authorization", "content-type", "mcp-protocol-version", "mcp-method", "mcp-name"} <= allowed
    assert "POST" in answered.headers["access-control-allow-methods"]


def test_a_browser_client_reads_the_mcp_reply_and_its_challenge_headers() -> None:
    answered = client().post("/api/mcp", json=INITIALIZE, headers={"Origin": BROWSER_CLIENT})
    assert answered.status_code == 200
    assert answered.headers["access-control-allow-origin"] == "*"
    exposed = answered.headers["access-control-expose-headers"].lower()
    assert "www-authenticate" in exposed and "retry-after" in exposed


def test_even_the_site_s_own_origin_gets_the_open_answer_never_credentials() -> None:
    answered = client().post("/api/mcp", json=INITIALIZE, headers={"Origin": "http://localhost:3000"})
    assert answered.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in answered.headers


def test_the_site_s_own_routes_keep_their_configured_origins() -> None:
    refused = preflight("/api/auth/login", "https://evil.example")
    assert refused.status_code == 400
    assert "access-control-allow-origin" not in refused.headers
    consent = preflight("/api/oauth/authorize/approve")
    assert consent.headers.get("access-control-allow-origin") != "*"
    assert is_open_path("/api/mcp/") and not is_open_path("/api/oauth/authorize/request")


@pytest.mark.parametrize(
    ("origin", "web"),
    [
        ("https://claude.ai", True),
        ("https://inspector.example:8443", True),
        ("http://localhost:6274", True),
        ("http://agents.example", True),
        ("chrome-extension://abcdefghijklmnop", True),
        ("null", False),
        ("https://evil.example/path", False),
        ("https://user@evil.example", False),
        ("file://", False),
        ("not an origin", False),
    ],
)
def test_any_origin_is_served_but_null_and_what_is_no_origin_at_all(origin: str, web: bool) -> None:
    assert is_web_origin(origin) is web
