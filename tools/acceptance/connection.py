from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from atomic_write import write_text_atomically

__all__ = [
    "PROTOCOL_VERSION",
    "REFRESH_MARGIN",
    "REVOKE_PATH",
    "TOKEN_FILE_SCHEMA_VERSION",
    "TOKEN_PATH",
    "Connection",
    "McpConnection",
    "McpRefused",
    "connection_text",
    "read_connection",
]

TOKEN_FILE_SCHEMA_VERSION = 1
PROTOCOL_VERSION = "2025-11-25"
REFRESH_MARGIN = timedelta(minutes=10)
TOKEN_PATH = "/api/oauth/token"
REVOKE_PATH = "/api/oauth/revoke"
CLIENT_INFO = {"name": "kalavigyan-agent-acceptance", "version": "1.0.0"}
TEXT_FIELDS = ("api", "server", "clientId", "accessToken", "refreshToken", "expiresAt")

Mask = Callable[[str], None]
Clock = Callable[[], datetime]


class McpRefused(RuntimeError):
    pass


@dataclass(frozen=True)
class Connection:
    api: str
    server: str
    client_id: str
    access_token: str
    refresh_token: str
    expires_at: datetime


def read_connection(path: Path) -> Connection:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schemaVersion") != TOKEN_FILE_SCHEMA_VERSION:
        raise ValueError(f"{path} is not a token file of schema version {TOKEN_FILE_SCHEMA_VERSION}")
    missing = [name for name in TEXT_FIELDS if not isinstance(data.get(name), str) or not data[name]]
    if missing:
        raise ValueError(f"{path} lacks {', '.join(missing)}")
    expires_at = datetime.fromisoformat(data["expiresAt"])
    if expires_at.tzinfo is None:
        raise ValueError(f"{path} gives expiresAt without a time zone")
    return Connection(
        api=data["api"],
        server=data["server"],
        client_id=data["clientId"],
        access_token=data["accessToken"],
        refresh_token=data["refreshToken"],
        expires_at=expires_at,
    )


def connection_text(connection: Connection) -> str:
    data = {
        "schemaVersion": TOKEN_FILE_SCHEMA_VERSION,
        "api": connection.api,
        "server": connection.server,
        "clientId": connection.client_id,
        "accessToken": connection.access_token,
        "refreshToken": connection.refresh_token,
        "expiresAt": connection.expires_at.isoformat(),
    }
    return json.dumps(data, indent=2) + "\n"


def _now() -> datetime:
    return datetime.now(UTC)


class McpConnection:
    def __init__(self, path: Path, http: httpx.Client, *, mask: Mask, clock: Clock = _now) -> None:
        self.path = path
        self.http = http
        self.mask = mask
        self.clock = clock
        self.connection = read_connection(path)
        mask(self.connection.access_token)
        mask(self.connection.refresh_token)

    @property
    def server(self) -> str:
        return self.connection.server

    def token(self) -> str:
        if self.clock() + REFRESH_MARGIN >= self.connection.expires_at:
            self._refresh()
        return self.connection.access_token

    def instructions(self) -> str:
        params = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": CLIENT_INFO}
        return str(self._rpc("initialize", params).get("instructions") or "")

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._rpc("tools/call", {"name": name, "arguments": arguments})

    def listed_tools(self) -> list[dict[str, Any]]:
        return list(self._rpc("tools/list", {}).get("tools") or [])

    def revoke(self) -> int:
        form = {"token": self.connection.refresh_token, "client_id": self.connection.client_id}
        return self.http.post(self.connection.api + REVOKE_PATH, data=form).status_code

    def _refresh(self) -> None:
        form = {
            "grant_type": "refresh_token",
            "refresh_token": self.connection.refresh_token,
            "client_id": self.connection.client_id,
        }
        response = self.http.post(self.connection.api + TOKEN_PATH, data=form)
        if response.status_code != httpx.codes.OK:
            raise McpRefused(
                f"the token refresh answered HTTP {response.status_code}: {_error_code(response)}"
            )
        body = response.json()
        self.mask(body["access_token"])
        self.mask(body["refresh_token"])
        self.connection = replace(
            self.connection,
            access_token=body["access_token"],
            refresh_token=body["refresh_token"],
            expires_at=self.clock() + timedelta(seconds=int(body["expires_in"])),
        )
        write_text_atomically(self.path, connection_text(self.connection))

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "authorization": f"Bearer {self.token()}",
            "accept": "application/json",
            "mcp-protocol-version": PROTOCOL_VERSION,
        }
        sent = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = self.http.post(self.connection.server, json=sent, headers=headers)
        if response.status_code != httpx.codes.OK:
            raise McpRefused(f"{method} answered HTTP {response.status_code}")
        body = response.json()
        if body.get("error"):
            raise McpRefused(f"{method} answered {body['error'].get('message')}")
        return body.get("result") or {}


def _error_code(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "no JSON error"
    return str(body.get("error")) if isinstance(body, dict) else "no JSON error"
