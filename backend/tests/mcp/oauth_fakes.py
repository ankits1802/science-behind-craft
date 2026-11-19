import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import oauth_hosts
from app.api.routes import mcp, oauth_consent
from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.main import create_app
from app.models import User

from ..readers import sign_in_as

__all__ = [
    "API",
    "RESOURCE",
    "RESOURCE_METADATA",
    "WEB",
    "FakeSession",
    "client",
    "person",
    "with_hosts",
]

API = "https://api.kalavigyan.example"
WEB = "https://kalavigyan.example"
RESOURCE = "https://api.kalavigyan.example/api/mcp"
RESOURCE_METADATA = "https://api.kalavigyan.example/.well-known/oauth-protected-resource/api/mcp"


@dataclass
class FakeSession:
    commits: int = 0
    rollbacks: int = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def person(role: str = "RESEARCHER") -> User:
    key = uuid.uuid4()
    return User(id=key, name=f"{role.title()} {key.hex[:4]}", email=f"{key.hex[:12]}@example.org", role=role)


def with_hosts(monkeypatch: pytest.MonkeyPatch, *, api: str | None = API, enabled: bool = True) -> Settings:
    settings = get_settings().model_copy(
        update={"public_api_url": api, "public_web_url": WEB, "mcp_server_enabled": enabled}
    )
    for module in (oauth_hosts, oauth_consent, mcp):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    return settings


def client(session: FakeSession | None = None, *, reader: User | None = None) -> TestClient:
    app = create_app()
    opened = session or FakeSession()

    async def fake_session() -> AsyncIterator[Any]:
        yield opened

    app.dependency_overrides[get_session] = fake_session
    if reader is not None:
        sign_in_as(app, lambda: reader)
    return TestClient(app)
