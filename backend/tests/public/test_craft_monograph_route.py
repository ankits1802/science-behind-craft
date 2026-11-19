import hashlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import craft_monograph as route
from app.core.db import get_session
from app.main import create_app
from app.research.monograph_document import MonographDocument
from app.services.answering import NOT_FOUND_DETAIL

PATH = "/api/crafts/kutch-ajrakh/monograph"
DIGEST = "a" * 64
STORED = {
    "schemaVersion": 1,
    "subjectKind": "craft",
    "subjectSlug": "Kutch-Ajrakh",
    "version": 3,
    "title": "Kutch Ajrakh",
}
GENERATED = MonographDocument.model_validate(
    {
        "subjectKind": "craft",
        "subjectSlug": "Kutch-Ajrakh",
        "title": "Kutch Ajrakh",
        "version": 1,
        "content": {
            "craftSlug": "Kutch-Ajrakh",
            "sources": {},
            "citations": {},
            "citationClaims": {},
            "data": {},
            "units": {},
            "components": [],
            "layout": [],
        },
        "pageUrl": "https://kalavigyan.example/crafts/Kutch-Ajrakh",
    }
)


@dataclass
class Calls:
    made: list[str] = field(default_factory=list)


def served(
    monkeypatch: pytest.MonkeyPatch, *, known: bool = True, stored: bool = True, generated: bool = False
) -> tuple[TestClient, Calls]:
    calls = Calls()

    async def resolve_craft(session: Any, slug: str) -> Any:
        calls.made.append(f"resolve {slug}")
        return SimpleNamespace(slug="Kutch-Ajrakh") if known else None

    async def latest_document_row(session: Any, subject_kind: str, slug: str) -> Any:
        calls.made.append(f"stored {subject_kind} {slug}")
        return SimpleNamespace(version=3, contentHash=DIGEST, document=STORED) if stored else None

    async def generated_fallback(session: Any, slug: str) -> MonographDocument | None:
        calls.made.append(f"generated {slug}")
        return GENERATED if generated else None

    async def session() -> AsyncIterator[object]:
        yield object()

    monkeypatch.setattr(route.knowledge_view, "resolve_craft", resolve_craft)
    monkeypatch.setattr(route, "latest_document_row", latest_document_row)
    monkeypatch.setattr(route, "generated_fallback", generated_fallback)
    app = create_app()
    app.dependency_overrides[get_session] = session
    return TestClient(app), calls


def test_the_latest_stored_document_is_served_with_its_version_tag_and_the_public_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, calls = served(monkeypatch)
    answer = http.get(PATH)
    assert answer.status_code == 200
    assert answer.json() == STORED
    assert answer.headers["etag"] == f'"v3-{DIGEST}"'
    assert answer.headers["cache-control"] == "public, max-age=300"
    assert "Authorization" in answer.headers["vary"]
    assert calls.made == ["resolve kutch-ajrakh", "stored craft Kutch-Ajrakh"]


def test_a_reader_holding_the_document_is_told_it_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    http, _ = served(monkeypatch)
    answer = http.get(PATH, headers={"If-None-Match": f'"v3-{DIGEST}"'})
    assert answer.status_code == 304
    assert answer.content == b""


def test_without_a_stored_document_the_generated_one_is_served(monkeypatch: pytest.MonkeyPatch) -> None:
    http, calls = served(monkeypatch, stored=False, generated=True)
    answer = http.get(PATH)
    body = GENERATED.model_dump(mode="json", by_alias=True)
    assert answer.status_code == 200 and answer.json() == body
    hashed = json.dumps(
        {k: v for k, v in body.items() if k != "version"}, sort_keys=True, separators=(",", ":")
    )
    assert answer.headers["etag"] == f'"v1-{hashlib.sha256(hashed.encode("utf-8")).hexdigest()}"'
    assert calls.made[-1] == "generated Kutch-Ajrakh"


@pytest.mark.parametrize(
    ("changes", "detail", "asked"),
    [
        ({"known": False}, NOT_FOUND_DETAIL, ["resolve kutch-ajrakh"]),
        (
            {"stored": False},
            route.NO_DOCUMENT_DETAIL,
            ["resolve kutch-ajrakh", "stored craft Kutch-Ajrakh", "generated Kutch-Ajrakh"],
        ),
    ],
    ids=["an unknown craft", "a craft with no document stored or generated"],
)
def test_a_craft_without_a_document_is_not_found(
    monkeypatch: pytest.MonkeyPatch, changes: dict[str, bool], detail: str, asked: list[str]
) -> None:
    http, calls = served(monkeypatch, **changes)
    answer = http.get(PATH)
    assert answer.status_code == 404
    assert answer.json()["detail"] == detail
    assert calls.made == asked


async def test_the_fallback_generates_nothing_until_generated_documents_exist() -> None:
    assert await route.generated_fallback(object(), "Kutch-Ajrakh") is None
