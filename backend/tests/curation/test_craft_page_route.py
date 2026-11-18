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

from ..contracts.golden import golden_text
from ..readers import sign_in_as
from .import_support import AJRAKH, AJRAKH_GOLDEN
from .test_craft_page import STUDENT_CLAIMS, ajrakh_records

PATH = f"/api/crafts/{AJRAKH}/page"


async def no_session() -> Any:
    yield None


def client_for(monkeypatch: pytest.MonkeyPatch, role: str) -> TestClient:
    async def resolve(_session: Any, slug: str) -> Any:
        return SimpleNamespace(slug=slug) if slug == AJRAKH else None

    async def records(_session: Any, _craft: Any, **_kwargs: Any) -> Any:
        return ajrakh_records()

    monkeypatch.setattr(knowledge_view, "resolve_craft", resolve)
    monkeypatch.setattr(crafts, "craft_page_records", records)
    app = create_app()
    reader = User(id=uuid.UUID(int=8), name=role.title(), email=f"{role.lower()}@example.com", role=role)
    sign_in_as(app, lambda: reader)
    app.dependency_overrides[get_session] = no_session
    return TestClient(app)


def test_a_student_gets_no_evidence_and_no_uncited_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    response = client_for(monkeypatch, "STUDENT").get(PATH)
    assert response.status_code == 200
    page = response.json()
    assert page["evidence"] is None
    assert len(page["claims"]) == STUDENT_CLAIMS
    full = json.loads(golden_text(AJRAKH_GOLDEN))
    hidden = {claim["id"] for claim in full["claims"]} - {claim["id"] for claim in page["claims"]}
    assert len(hidden) == len(full["claims"]) - STUDENT_CLAIMS
    assert hidden.isdisjoint(
        json.dumps({key: value for key, value in page.items() if key != "claims"}).split('"')
    )


@pytest.mark.parametrize("role", ["RESEARCHER", "PROFESSOR", "MASTER_ADMIN"])
def test_a_researcher_and_above_get_the_whole_page(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
    response = client_for(monkeypatch, role).get(PATH)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-cache"
    assert response.json() == json.loads(golden_text(AJRAKH_GOLDEN))
