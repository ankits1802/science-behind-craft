from dataclasses import replace
from typing import Any

import pytest

from app.api.routes import crafts

from .test_craft_page import ajrakh_records
from .test_craft_page_route import PATH, client_for

NOT_MODIFIED = 304


def test_a_repeat_read_with_the_page_tag_is_not_modified(monkeypatch: pytest.MonkeyPatch) -> None:
    client = client_for(monkeypatch, "RESEARCHER")
    first = client.get(PATH)
    tag = first.headers["etag"]
    assert first.status_code == 200 and tag.startswith('"')
    again = client.get(PATH, headers={"If-None-Match": tag})
    assert (again.status_code, again.content, again.headers["etag"]) == (NOT_MODIFIED, b"", tag)


def test_each_view_of_the_page_has_its_own_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    researcher = client_for(monkeypatch, "RESEARCHER").get(PATH).headers["etag"]
    student = client_for(monkeypatch, "STUDENT")
    assert student.get(PATH).headers["etag"] != researcher
    assert student.get(PATH, headers={"If-None-Match": researcher}).status_code == 200


def test_a_new_curation_version_changes_the_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    client = client_for(monkeypatch, "RESEARCHER")
    tag = client.get(PATH).headers["etag"]
    records = ajrakh_records()
    assert records.curated is not None
    newer = replace(
        records, curated=records.curated.model_copy(update={"version": records.curated.version + 1})
    )

    async def curated_again(_session: Any, _craft: Any, **_kwargs: Any) -> Any:
        return newer

    monkeypatch.setattr(crafts, "craft_page_records", curated_again)
    response = client.get(PATH, headers={"If-None-Match": tag})
    assert response.status_code == 200
    assert response.headers["etag"] != tag
    assert response.json()["curation"]["version"] == records.curated.version + 1
