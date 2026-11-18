import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import crafts
from app.core.db import get_session
from app.main import create_app
from app.models import User
from app.services import knowledge_view
from app.services.answering import NOT_FOUND_DETAIL

from ..contracts.golden import golden_text
from ..readers import sign_in_as
from .golden_process import GOLDEN, golden_records

AJRAKH = SimpleNamespace(id=uuid.UUID(int=11), slug="Kutch-Ajrakh", name="Kutch Ajrakh")


async def no_session() -> Any:
    yield None


@pytest.fixture
def signed_in(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def resolve(_session: Any, slug: str) -> Any:
        return AJRAKH if slug == "Kutch-Ajrakh" else None

    async def records(_session: Any, craft: Any, **_kwargs: Any) -> Any:
        assert craft is AJRAKH
        return golden_records()

    monkeypatch.setattr(knowledge_view, "resolve_craft", resolve)
    monkeypatch.setattr(crafts, "process_records", records)
    app = create_app()
    student = User(id=uuid.UUID(int=7), name="Asha", email="asha@example.com", role="STUDENT")
    sign_in_as(app, lambda: student)
    app.dependency_overrides[get_session] = no_session
    return TestClient(app)


def test_the_process_route_answers_the_golden_process(signed_in: TestClient) -> None:
    response = signed_in.get("/api/crafts/Kutch-Ajrakh/process")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-cache"
    assert response.json() == json.loads(golden_text(GOLDEN))


def test_an_unknown_craft_has_no_process(signed_in: TestClient) -> None:
    response = signed_in.get("/api/crafts/No-Such-Craft/process")
    assert (response.status_code, response.json()) == (404, {"detail": NOT_FOUND_DETAIL})
