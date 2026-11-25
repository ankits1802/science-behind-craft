from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from app.api import document_reads
from app.api.routes import craft_monograph as route
from app.research.page_revalidation import PageOwners
from app.services.stored_documents import GeneratedRead

from .test_craft_monograph_route import (
    GENERATED,
    PATH,
    VARIANT_DIGEST,
    Calls,
    generated_digest,
    served,
    stored_copy,
)

REBUILT = GENERATED.model_copy(update={"version": 2, "title": "Kutch Ajrakh, rebuilt"})


def rebuilt_since(monkeypatch: pytest.MonkeyPatch, calls: Calls) -> None:
    async def generated_fallback(session: Any, craft: Any) -> GeneratedRead:
        calls.made.append(f"generated {craft.slug}")
        subject = SimpleNamespace(kind="craft", slug=craft.slug)
        return GeneratedRead(subject, stored_copy(REBUILT, current=False), rebuild=True)  # type: ignore[arg-type]

    monkeypatch.setattr(route, "generated_fallback", generated_fallback)
    calls.kept[1] = stored_copy(GENERATED, current=False)


def test_a_generated_page_still_reads_the_version_its_rebuild_replaced_in_english_and_in_its_languages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, calls = served(monkeypatch, stored=False, generated=True)
    rebuilt_since(monkeypatch, calls)
    earlier = http.get(PATH, params={"version": 1})
    assert earlier.status_code == 200
    assert earlier.content == stored_copy(GENERATED).text.encode("utf-8")
    assert earlier.headers["etag"] == f'"v1-{generated_digest()}"'
    assert earlier.headers["content-language"] == "en"
    assert calls.made[-1] == "superseded craft Kutch-Ajrakh 1"
    assert calls.queued == [("craft", "Kutch-Ajrakh")]
    assert calls.languages == []
    first = http.get(PATH, params={"version": 1, "part": 0}).json()
    assert (first["version"], first["tag"]) == (1, f"v1-{generated_digest()}")
    hindi = http.get(PATH, params={"version": 1, "lang": "hi"})
    assert hindi.status_code == 200
    assert hindi.headers["content-language"] == "hi"
    assert hindi.headers["etag"] == f'"v1-{generated_digest()}-hi-{VARIANT_DIGEST}"'
    assert hindi.json()["version"] == 1
    page = ("craft", "Kutch-Ajrakh")
    assert calls.translated[-1] == (page, f"v1-{generated_digest()}", "hi")
    hindi_part = http.get(PATH, params={"version": 1, "lang": "hi", "part": 0}).json()
    assert hindi_part["tag"] == f"v1-{generated_digest()}-hi-{VARIANT_DIGEST}"
    assert calls.languages == []
    assert http.get(PATH).json()["title"] == "Kutch Ajrakh, rebuilt"
    assert http.get(PATH, params={"version": 2}).json()["version"] == 2


def test_a_generated_page_s_version_never_kept_is_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    http, calls = served(monkeypatch, stored=False, generated=True)
    rebuilt_since(monkeypatch, calls)
    missing = http.get(PATH, params={"version": 7})
    assert missing.status_code == 404
    assert missing.json()["detail"] == route.NO_VERSION_DETAIL
    assert calls.made[-1] == "superseded craft Kutch-Ajrakh 7"


def asked_refreshes(monkeypatch: pytest.MonkeyPatch, *, by_web: bool, claims: list[bool]) -> list[Any]:
    seen: list[Any] = []

    async def claim_refresh(session: Any, subject: Any, *, now: Any) -> bool:
        seen.append(f"claim {subject.kind} {subject.slug}")
        return claims.pop(0)

    async def refresh_pages(owners: Any) -> bool:
        seen.append(owners)
        return True

    monkeypatch.setattr(document_reads, "is_web_server_read", lambda request: by_web)
    monkeypatch.setattr(document_reads, "claim_refresh", claim_refresh)
    monkeypatch.setattr(document_reads, "refresh_pages", refresh_pages)
    return seen


def test_the_web_reading_a_version_no_longer_served_asks_once_for_the_page_s_refresh_and_finds_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, calls = served(monkeypatch, stored=False, generated=True)
    rebuilt_since(monkeypatch, calls)
    calls.kept.clear()
    seen = asked_refreshes(monkeypatch, by_web=True, claims=[True, False])
    gone = http.get(PATH, params={"version": 1, "part": 0})
    assert gone.status_code == 404
    assert gone.json()["detail"] == route.NO_VERSION_DETAIL
    assert seen == ["claim craft Kutch-Ajrakh", PageOwners(crafts=("Kutch-Ajrakh",))]
    assert http.get(PATH, params={"version": 1}).status_code == 404
    assert seen[2:] == ["claim craft Kutch-Ajrakh"]


def test_a_visitor_s_read_a_version_above_the_current_or_one_still_kept_asks_no_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, calls = served(monkeypatch, stored=False, generated=True)
    rebuilt_since(monkeypatch, calls)
    seen = asked_refreshes(monkeypatch, by_web=False, claims=[])
    calls.kept.clear()
    assert http.get(PATH, params={"version": 1}).status_code == 404
    web = asked_refreshes(monkeypatch, by_web=True, claims=[])
    assert http.get(PATH, params={"version": 7}).status_code == 404
    calls.kept[1] = stored_copy(GENERATED, current=False)
    assert http.get(PATH, params={"version": 1}).status_code == 200
    assert (seen, web) == ([], [])


def test_a_version_a_removal_reached_is_served_to_a_read_naming_it_and_marked_withheld(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    http, calls = served(monkeypatch, stored=False, generated=True)
    rebuilt_since(monkeypatch, calls)
    calls.kept[1] = replace(stored_copy(GENERATED, current=False), withheld=True)
    read = http.get(PATH, params={"version": 1})
    assert read.status_code == 200
    assert read.json()["version"] == 1
    assert read.headers["etag"] == f'"v1-{generated_digest()}"'
