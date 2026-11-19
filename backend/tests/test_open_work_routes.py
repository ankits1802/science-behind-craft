from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import open_work as routes
from app.core.db import get_session
from app.main import create_app
from app.research.open_work import OpenWork, Viewer, WorkFilters


async def no_session() -> AsyncIterator[Any]:
    yield None


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = no_session
    return TestClient(app)


def test_open_work_takes_its_filters_from_the_query_and_serves_anyone(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}

    async def listed(
        session: Any, filters: WorkFilters, viewer: Viewer, *, site: str, now: datetime
    ) -> OpenWork:
        seen.update(filters=filters, viewer=viewer)
        return OpenWork(filters=filters, total=0, reservation_minutes=120, tasks=[])

    monkeypatch.setattr(routes.open_work, "list_open_work", listed)
    response = client.get(
        "/api/knowledge/open-work", params={"craftSlug": "Kutch-Ajrakh", "field": "HISTORY", "limit": 5}
    )
    assert response.status_code == 200, response.text
    assert seen == {
        "filters": WorkFilters(craft_slug="Kutch-Ajrakh", field="HISTORY", limit=5),
        "viewer": Viewer(),
    }
    assert response.json()["filters"]["craftSlug"] == "Kutch-Ajrakh"


@pytest.mark.parametrize(
    "params",
    [
        {"craftSlug": "Kutch-Ajrakh", "familySlug": "Cane-Bamboo-Craft"},
        {"kind": "GUESS"},
        {"limit": 500},
    ],
)
def test_wrong_filters_are_refused(client: TestClient, params: dict[str, Any]) -> None:
    assert client.get("/api/knowledge/open-work", params=params).status_code == 422


def test_claiming_and_releasing_need_a_signed_in_contributor(client: TestClient) -> None:
    body = {"taskKey": "THIN_FIELD:craft:Kutch-Ajrakh:HISTORY"}
    assert client.post("/api/knowledge/open-work/claim", json=body).status_code == 401
    assert client.post("/api/knowledge/open-work/release", json=body).status_code == 401
