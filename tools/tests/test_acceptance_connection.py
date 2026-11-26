from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from acceptance_support import REPO

from acceptance.connection import (
    Connection,
    McpConnection,
    McpRefused,
    connection_text,
    read_connection,
)

GOLDEN = REPO / "shared" / "agent-acceptance.token.golden.json"
EXPIRES = datetime(2026, 11, 26, 11, 0, tzinfo=UTC)
OLD_ACCESS = "kvmcp_at_golden-not-a-token"
OLD_REFRESH = "kvmcp_rt_golden-not-a-token"
CLIENT_ID = "0b7f6f0e-3c1a-4c55-9a43-0f2b6a1e9d11"


def copied(tmp_path: Path) -> Path:
    target = tmp_path / "token.json"
    shutil.copyfile(GOLDEN, target)
    return target


def connected(path: Path, handler, now: datetime) -> tuple[McpConnection, list[str], list[httpx.Request]]:
    masked: list[str] = []
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    http = httpx.Client(transport=httpx.MockTransport(answer))
    return McpConnection(path, http, mask=masked.append, clock=lambda: now), masked, seen


def form(request: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(request.content.decode("ascii"))


def test_the_sign_in_s_token_file_reads_as_its_connection() -> None:
    assert read_connection(GOLDEN) == Connection(
        api="https://api.example",
        server="https://api.example/api/mcp",
        client_id=CLIENT_ID,
        access_token=OLD_ACCESS,
        refresh_token=OLD_REFRESH,
        expires_at=EXPIRES,
    )


def test_a_written_token_file_reads_back_as_the_same_connection(tmp_path: Path) -> None:
    path = tmp_path / "token.json"
    path.write_text(connection_text(read_connection(GOLDEN)), encoding="utf-8")
    assert read_connection(path) == read_connection(GOLDEN)


def test_a_token_file_without_a_field_or_of_another_version_is_refused(tmp_path: Path) -> None:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    path = tmp_path / "token.json"
    path.write_text(json.dumps({**data, "refreshToken": ""}), encoding="utf-8")
    with pytest.raises(ValueError, match="refreshToken"):
        read_connection(path)
    path.write_text(json.dumps({**data, "schemaVersion": 2}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema version 1"):
        read_connection(path)
    path.write_text(json.dumps({**data, "expiresAt": "2026-11-26T11:00:00"}), encoding="utf-8")
    with pytest.raises(ValueError, match="time zone"):
        read_connection(path)


def test_both_tokens_are_masked_as_soon_as_they_are_read(tmp_path: Path) -> None:
    _, masked, _ = connected(
        copied(tmp_path), lambda request: httpx.Response(500), EXPIRES - timedelta(hours=1)
    )
    assert masked == [OLD_ACCESS, OLD_REFRESH]


def test_a_token_well_before_its_hour_is_used_without_a_refresh(tmp_path: Path) -> None:
    server, _, seen = connected(
        copied(tmp_path), lambda request: httpx.Response(500), EXPIRES - timedelta(minutes=11)
    )
    assert server.token() == OLD_ACCESS
    assert seen == []


def test_a_token_near_its_hour_is_refreshed_masked_and_written_back(tmp_path: Path) -> None:
    now = EXPIRES - timedelta(minutes=9)
    fresh = {"access_token": "kvmcp_at_new", "refresh_token": "kvmcp_rt_new", "expires_in": 3600}
    path = copied(tmp_path)
    server, masked, seen = connected(path, lambda request: httpx.Response(200, json=fresh), now)
    assert server.token() == "kvmcp_at_new"
    assert str(seen[0].url) == "https://api.example/api/oauth/token"
    assert form(seen[0]) == {
        "grant_type": ["refresh_token"],
        "refresh_token": [OLD_REFRESH],
        "client_id": [CLIENT_ID],
    }
    assert masked[-2:] == ["kvmcp_at_new", "kvmcp_rt_new"]
    stored = read_connection(path)
    assert (stored.access_token, stored.refresh_token) == ("kvmcp_at_new", "kvmcp_rt_new")
    assert stored.expires_at == now + timedelta(hours=1)


def test_a_refused_refresh_names_the_error_and_never_a_token(tmp_path: Path) -> None:
    refused = httpx.Response(400, json={"error": "invalid_grant"})
    server, _, _ = connected(copied(tmp_path), lambda request: refused, EXPIRES)
    with pytest.raises(McpRefused, match="invalid_grant") as raised:
        server.token()
    assert OLD_ACCESS not in str(raised.value) and OLD_REFRESH not in str(raised.value)


def test_initialize_reads_the_server_s_instructions_with_the_bearer(tmp_path: Path) -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "result": {"instructions": "Start with find_crafts."}}
        )

    server, _, seen = connected(copied(tmp_path), answer, EXPIRES - timedelta(hours=1))
    assert server.instructions() == "Start with find_crafts."
    sent = json.loads(seen[0].content)
    assert (sent["method"], sent["params"]["protocolVersion"]) == ("initialize", "2025-11-25")
    assert seen[0].headers["authorization"] == f"Bearer {OLD_ACCESS}"
    assert seen[0].headers["accept"] == "application/json"


def test_a_tool_call_the_server_refuses_is_raised(tmp_path: Path) -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "bad draft"}}
        )

    server, _, _ = connected(copied(tmp_path), answer, EXPIRES - timedelta(hours=1))
    with pytest.raises(McpRefused, match="bad draft"):
        server.call_tool("preview_page", {"draft_id": "d1"})
    failing, _, _ = connected(
        copied(tmp_path), lambda request: httpx.Response(401), EXPIRES - timedelta(hours=1)
    )
    with pytest.raises(McpRefused, match="HTTP 401"):
        failing.call_tool("preview_page", {"draft_id": "d1"})


def test_revoking_sends_the_refresh_token_and_the_client_id(tmp_path: Path) -> None:
    server, _, seen = connected(
        copied(tmp_path), lambda request: httpx.Response(200), EXPIRES - timedelta(hours=1)
    )
    assert server.revoke() == 200
    assert str(seen[0].url) == "https://api.example/api/oauth/revoke"
    assert form(seen[0]) == {"token": [OLD_REFRESH], "client_id": [CLIENT_ID]}
