import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, SettingsError, get_settings
from app.main import create_app

PROJECT = "kalavigyan"
SCOPE = "cxacraftecosystem-8028s-projects"
PREVIEW = "https://kalavigyan-ab12cd34e-cxacraftecosystem-8028s-projects.vercel.app"
REFUSED = (
    "https://evil.vercel.app",
    "https://kalavigyan.vercel.app.evil.example",
    "https://kalavigyan-ab12cd34e-someone-else.vercel.app",
    "https://kalavigyan-ab12cd34e-cxacraftecosystem-8028s-projects.vercel.app.evil.example",
    "http://kalavigyan-ab12cd34e-cxacraftecosystem-8028s-projects.vercel.app",
    "https://kalavigyan-ab12cd34-cxacraftecosystem-8028s-projects.vercel.app",
    "https://kalavigyan-git-main-cxacraftecosystem-8028s-projects.vercel.app",
    "https://other-ab12cd34e-cxacraftecosystem-8028s-projects.vercel.app",
    "https://kalavigyanXab12cd34eXcxacraftecosystem-8028s-projectsXvercelXapp",
)


def preview_settings(**values: str) -> Settings:
    return Settings(_env_file=None, **values)


@pytest.fixture(autouse=True)
def no_preview_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BACKEND_CORS_PREVIEW_PROJECT", raising=False)
    monkeypatch.delenv("BACKEND_CORS_PREVIEW_SCOPE", raising=False)


@pytest.fixture
def preview_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("BACKEND_CORS_PREVIEW_PROJECT", PROJECT)
    monkeypatch.setenv("BACKEND_CORS_PREVIEW_SCOPE", SCOPE)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_no_preview_origin_is_allowed_by_default() -> None:
    assert preview_settings().cors_origin_regex is None


def test_the_preview_rule_matches_only_this_projects_deployment_hosts() -> None:
    rule = preview_settings(
        BACKEND_CORS_PREVIEW_PROJECT=PROJECT, BACKEND_CORS_PREVIEW_SCOPE=SCOPE
    ).cors_origin_regex
    assert rule == r"https://kalavigyan-[a-z0-9]{9}-cxacraftecosystem\-8028s\-projects\.vercel\.app"
    assert re.fullmatch(rule, PREVIEW)
    for origin in REFUSED:
        assert re.fullmatch(rule, origin) is None, origin


@pytest.mark.parametrize(
    "values",
    [
        {"BACKEND_CORS_PREVIEW_PROJECT": PROJECT},
        {"BACKEND_CORS_PREVIEW_SCOPE": SCOPE},
        {"BACKEND_CORS_PREVIEW_PROJECT": "kala.*", "BACKEND_CORS_PREVIEW_SCOPE": SCOPE},
        {"BACKEND_CORS_PREVIEW_PROJECT": PROJECT, "BACKEND_CORS_PREVIEW_SCOPE": "*"},
        {"BACKEND_CORS_PREVIEW_PROJECT": "KalaVigyan", "BACKEND_CORS_PREVIEW_SCOPE": SCOPE},
    ],
)
def test_a_half_set_or_wildcard_preview_rule_is_refused(values: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        preview_settings(**values)


def test_a_half_set_preview_rule_stops_the_app_from_starting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BACKEND_CORS_PREVIEW_PROJECT", PROJECT)
    get_settings.cache_clear()
    try:
        with pytest.raises(SettingsError, match=r"(?i)cors_preview_scope"):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_the_api_answers_a_preflight_from_a_preview_and_refuses_a_stranger(preview_env: None) -> None:
    client = TestClient(create_app())
    asked = {"Access-Control-Request-Method": "POST"}
    preview = client.options("/api/auth/login", headers={"Origin": PREVIEW, **asked})
    assert preview.status_code == 200
    assert preview.headers["access-control-allow-origin"] == PREVIEW
    assert preview.headers["access-control-allow-credentials"] == "true"
    stranger = client.options("/api/auth/login", headers={"Origin": "https://evil.vercel.app", **asked})
    assert stranger.status_code == 400
    assert "access-control-allow-origin" not in stranger.headers
    production = client.options("/api/auth/login", headers={"Origin": "http://localhost:3000", **asked})
    assert production.headers["access-control-allow-origin"] == "http://localhost:3000"
