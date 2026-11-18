from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import crafts
from app.core.http_cache import body_version
from app.services.craft_page_cache import ServedPage, served_content

from .test_craft_page_route import PATH, client_for, golden

NOT_MODIFIED = 304


def served_bodies(monkeypatch: pytest.MonkeyPatch, bodies: dict[str, dict[str, Any]]) -> None:
    async def page(_session: Any, _craft: Any, variant: str, **_options: Any) -> ServedPage:
        body = bodies[variant]
        return ServedPage(served_content(body), body_version(body), variant)

    monkeypatch.setattr(crafts, "served_page", page)


def researcher_quoting(body: dict[str, Any]) -> dict[str, Any]:
    return {**body, "suggestedQuestions": [*body["suggestedQuestions"], "A closed quote's question"]}


def client(monkeypatch: pytest.MonkeyPatch, role: str, bodies: dict[str, dict[str, Any]]) -> TestClient:
    made = client_for(monkeypatch, role, [])
    served_bodies(monkeypatch, bodies)
    return made


def test_a_repeat_read_with_the_page_tag_is_not_modified(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = client(monkeypatch, "RESEARCHER", {"RESEARCHER": golden()})
    first = reader.get(PATH)
    tag = first.headers["etag"]
    assert first.status_code == 200 and tag.startswith('"')
    again = reader.get(PATH, headers={"If-None-Match": tag})
    assert (again.status_code, again.content, again.headers["etag"]) == (NOT_MODIFIED, b"", tag)


def test_each_variant_of_the_page_has_its_own_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    bodies = {"OPEN": golden(), "RESEARCHER": researcher_quoting(golden())}
    researcher = client(monkeypatch, "RESEARCHER", bodies).get(PATH).headers["etag"]
    student = client(monkeypatch, "STUDENT", bodies)
    assert student.get(PATH).headers["etag"] != researcher
    assert student.get(PATH, headers={"If-None-Match": researcher}).status_code == 200


def test_a_new_body_changes_the_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    bodies = {"OPEN": golden()}
    reader = client(monkeypatch, "STUDENT", bodies)
    tag = reader.get(PATH).headers["etag"]
    newer = golden()
    newer["curation"] = {**newer["curation"], "version": newer["curation"]["version"] + 1}
    bodies["OPEN"] = newer
    response = reader.get(PATH, headers={"If-None-Match": tag})
    assert response.status_code == 200
    assert response.headers["etag"] != tag
