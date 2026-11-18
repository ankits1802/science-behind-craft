import dataclasses
import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import crafts, map_layers
from app.core.db import get_session
from app.main import create_app
from app.models import User
from app.services import knowledge_view
from app.services.answering import NOT_FOUND_DETAIL

from ..contracts.golden import golden_text
from ..readers import sign_in_as
from .golden_region import (
    GOLDEN_CRAFT,
    GOLDEN_LAYER,
    GOLDEN_LAYERS,
    golden_layer_values,
    golden_listing,
    golden_region_records,
)

AJRAKH = SimpleNamespace(id=uuid.UUID(int=11), slug="Kutch-Ajrakh", name="Kutch Ajrakh")


async def no_session() -> Any:
    yield None


@pytest.fixture
def signed_in(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def resolve(_session: Any, slug: str) -> Any:
        return AJRAKH if slug == "Kutch-Ajrakh" else None

    async def records(_session: Any, craft: Any) -> Any:
        assert craft is AJRAKH
        return golden_region_records()

    async def listing(_session: Any) -> Any:
        return golden_listing()

    async def values(_session: Any, spec: Any) -> Any:
        return golden_layer_values() if spec.id == "soil-ph-0-5cm" else None

    monkeypatch.setattr(knowledge_view, "resolve_craft", resolve)
    monkeypatch.setattr(crafts, "region_records", records)
    monkeypatch.setattr(map_layers, "listed_layers", listing)
    monkeypatch.setattr(map_layers, "layer_values", values)
    app = create_app()
    student = User(id=uuid.UUID(int=7), name="Asha", email="asha@example.com", role="STUDENT")
    sign_in_as(app, lambda: student)
    app.dependency_overrides[get_session] = no_session
    return TestClient(app)


def test_the_region_route_answers_the_golden_region(signed_in: TestClient) -> None:
    response = signed_in.get("/api/crafts/Kutch-Ajrakh/region")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-cache"
    assert response.json() == json.loads(golden_text(GOLDEN_CRAFT))


def test_an_unknown_craft_has_no_region(signed_in: TestClient) -> None:
    response = signed_in.get("/api/crafts/No-Such-Craft/region")
    assert (response.status_code, response.json()) == (404, {"detail": NOT_FOUND_DETAIL})


def test_the_layer_list_answers_the_golden_list(signed_in: TestClient) -> None:
    response = signed_in.get("/api/map/layers")
    assert (response.status_code, response.headers["cache-control"]) == (200, "private, no-cache")
    assert response.json() == json.loads(golden_text(GOLDEN_LAYERS))


def test_without_the_boundary_row_there_is_no_layer_list(
    signed_in: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def bare(_session: Any) -> Any:
        return dataclasses.replace(golden_listing(), layers=(), datasets={}, boundary=None)

    monkeypatch.setattr(map_layers, "listed_layers", bare)
    response = signed_in.get("/api/map/layers")
    assert (response.status_code, response.json()) == (404, {"detail": map_layers.NO_LAYERS_DETAIL})


def test_a_layer_answers_its_golden_body_and_its_version_as_etag(signed_in: TestClient) -> None:
    golden = json.loads(golden_text(GOLDEN_LAYER))
    response = signed_in.get("/api/map/layers/soil-ph-0-5cm")
    assert response.status_code == 200
    assert response.json() == golden
    assert (response.headers["etag"], response.headers["cache-control"]) == (
        f'"{golden["version"]}"',
        "private, no-cache",
    )
    again = signed_in.get(
        "/api/map/layers/soil-ph-0-5cm", headers={"If-None-Match": response.headers["etag"]}
    )
    assert (again.status_code, again.content, again.headers["etag"]) == (304, b"", response.headers["etag"])


@pytest.mark.parametrize("layer", ["elevation", "rainfall"])
def test_an_empty_or_unknown_layer_is_not_found(signed_in: TestClient, layer: str) -> None:
    response = signed_in.get(f"/api/map/layers/{layer}")
    assert (response.status_code, response.json()) == (404, {"detail": map_layers.NO_LAYER_DETAIL})
