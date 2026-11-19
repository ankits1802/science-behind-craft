from collections.abc import AsyncIterator
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.mcp import mcp_enabled
from app.core.config import get_settings
from app.core.db import get_session
from app.main import create_app

INITIALIZE = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}


async def no_session() -> AsyncIterator[Any]:
    yield None


def client(*, enabled: bool) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = no_session
    if enabled:
        app.dependency_overrides[mcp_enabled] = lambda: None
    return TestClient(app)


def test_the_server_answers_404_until_it_is_switched_on() -> None:
    assert get_settings().mcp_server_enabled is False
    response = client(enabled=False).post("/api/mcp", json=INITIALIZE)
    assert response.status_code == 404


def test_a_switched_on_server_initializes_over_plain_json() -> None:
    response = client(enabled=True).post("/api/mcp", json=INITIALIZE)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["result"]["protocolVersion"] == "2025-06-18"


def test_a_notification_is_accepted_without_a_body() -> None:
    response = client(enabled=True).post(
        "/api/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}
    )
    assert (response.status_code, response.content) == (202, b"")


def test_a_body_that_is_not_json_is_a_parse_error() -> None:
    response = client(enabled=True).post(
        "/api/mcp", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32700


def test_an_origin_that_is_no_origin_and_an_unknown_protocol_version_are_refused() -> None:
    for refused in ("null", "https://evil.example/path", "file://"):
        answered = client(enabled=True).post("/api/mcp", json=INITIALIZE, headers={"origin": refused})
        assert answered.status_code == 403, refused
    for served in ("https://inspector.example", "http://agents.example", get_settings().cors_origins[0]):
        answered = client(enabled=True).post("/api/mcp", json=INITIALIZE, headers={"origin": served})
        assert answered.status_code == 200, served
    stale = client(enabled=True).post(
        "/api/mcp", json=INITIALIZE, headers={"mcp-protocol-version": "1999-01-01"}
    )
    assert stale.status_code == 400


def test_the_server_offers_no_event_stream() -> None:
    assert client(enabled=True).get("/api/mcp").status_code == 405
