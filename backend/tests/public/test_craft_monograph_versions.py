from types import SimpleNamespace
from typing import Any

import pytest

from app.api.routes import craft_monograph as route
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
