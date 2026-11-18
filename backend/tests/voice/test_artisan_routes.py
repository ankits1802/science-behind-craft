import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import artisan_deps
from app.main import create_app
from app.voice.artisan_availability import HIDDEN_CONVERSATION

from ..test_knowledge import signed_in
from .test_artisan_session import voice

SOME_ID = uuid.UUID(int=5)
GUARDED = [
    ("POST", "/api/artisan/conversations"),
    ("POST", f"/api/artisan/conversations/{SOME_ID}/turns"),
    ("GET", f"/api/artisan/conversations/{SOME_ID}/turns/{SOME_ID}/speech"),
    ("POST", f"/api/artisan/conversations/{SOME_ID}/end"),
    ("POST", "/api/artisan/llm/v1/chat/completions"),
]


@pytest.mark.parametrize(("method", "path"), GUARDED)
def test_every_conversation_route_is_not_found_while_the_switch_is_off(method: str, path: str) -> None:
    client = TestClient(create_app())
    assert client.request(method, path, json={}).status_code == 404


@pytest.mark.parametrize(("method", "path"), GUARDED[:4])
def test_with_the_switch_on_the_routes_need_a_session(method: str, path: str) -> None:
    app = create_app()
    app.dependency_overrides[artisan_deps.artisan_conversation_enabled] = lambda: True
    assert TestClient(app).request(method, path, json={}).status_code == 401


def test_the_custom_llm_route_refuses_a_call_without_the_bearer_when_on() -> None:
    app = create_app()
    app.dependency_overrides[artisan_deps.artisan_conversation_enabled] = lambda: True
    app.dependency_overrides[artisan_deps.artisan_voice_settings] = lambda: voice("AGENT")
    response = TestClient(app).post("/api/artisan/llm/v1/chat/completions", json={})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_the_answers_config_hides_conversations_while_the_switch_is_off() -> None:
    body = signed_in("ARTISAN").get("/api/answers/config").json()
    assert body["conversation"] == HIDDEN_CONVERSATION
