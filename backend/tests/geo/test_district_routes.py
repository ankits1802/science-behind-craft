import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import map_districts
from app.core.db import get_session
from app.core.deps import get_current_user
from app.main import create_app
from app.models import User

from .test_district_view import golden, records

PATH = "/api/map/districts/449"


async def no_session() -> Any:
    yield None


@pytest.fixture
def signed_in(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    asked: list[int] = []

    async def stored(_session: Any, district_lgd: int) -> Any:
        asked.append(district_lgd)
        return records() if district_lgd == 449 else None

    monkeypatch.setattr(map_districts, "district_records", stored)
    app = create_app()
    student = User(id=uuid.UUID(int=7), name="Asha", email="asha@example.com", role="STUDENT")
    app.dependency_overrides[get_current_user] = lambda: student
    app.dependency_overrides[get_session] = no_session
    client = TestClient(app)
    client.asked = asked
    return client


def test_ask_the_map_needs_a_session() -> None:
    assert TestClient(create_app()).get(PATH).status_code == 401


def test_a_tapped_district_answers_its_stored_crafts_and_land(signed_in: TestClient) -> None:
    response = signed_in.get(PATH)
    assert (response.status_code, response.headers["cache-control"]) == (200, "private, no-cache")
    assert response.json() == golden()
    blocks = response.json()["land"]["blocks"]
    assert blocks and all(block["reuse"]["pieceId"] for block in blocks)


def test_a_district_the_register_does_not_hold_is_not_found(signed_in: TestClient) -> None:
    response = signed_in.get("/api/map/districts/99999")
    assert (response.status_code, response.json()) == (404, {"detail": map_districts.NO_DISTRICT_DETAIL})


@pytest.mark.parametrize("code", ["0", "-3", "kachchh"])
def test_a_code_no_district_can_have_is_refused_before_any_read(signed_in: TestClient, code: str) -> None:
    assert signed_in.get(f"/api/map/districts/{code}").status_code == 422
    assert signed_in.asked == []
