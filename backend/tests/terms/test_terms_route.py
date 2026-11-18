import uuid
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.routes import terms
from app.composer.term_summary import term_summary_schema
from app.main import create_app
from app.models import User
from app.research.terms import Term
from app.services.term_summaries import NEEDS_LOOKUP_MESSAGE, StoredClaims, StoredTermLookup, TermLookup

from ..answering.fakes import translation
from ..readers import sign_in_as
from .fakes import CHECKED_AT, KUT_ID, FakeResearch, FakeTermStore, golden_claims, golden_term, kut_term

SCHEMA_KEYWORDS = {"type", "properties", "required", "additionalProperties", "items"}


def signed_in(role: str, store: FakeTermStore | None = None) -> TestClient:
    app = create_app()
    user = User(id=uuid.UUID(int=8), name="Ravi", email="ravi@example.com", role=role)
    kept = store or FakeTermStore({"kut": kut_term()}, stored=golden_claims())
    lookup = TermLookup(
        store=kept, research=FakeResearch(None), translation=translation(), clock=lambda: CHECKED_AT
    )
    sign_in_as(app, lambda: user)
    app.dependency_overrides[terms.term_lookup] = lambda: lookup
    return TestClient(app)


def anonymous(monkeypatch: pytest.MonkeyPatch, store: FakeTermStore) -> TestClient:
    monkeypatch.setattr(terms, "sessionmaker", lambda: None)
    monkeypatch.setattr(terms, "stored_term_lookup", lambda _sessions, **_kwargs: StoredTermLookup(store))
    return TestClient(create_app())


def test_an_anonymous_summary_from_stored_claims_keeps_one_etag_between_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = datetime(2026, 10, 2, 8, 15, tzinfo=UTC)
    store = FakeTermStore({"kut": kut_term()}, stored=replace(golden_claims(), changed_at=changed))
    client = anonymous(monkeypatch, store)
    first = client.get("/api/terms/kut")
    second = client.get("/api/terms/kut")
    assert first.json()["checkedAt"] == "2026-10-02T08:15:00Z"
    assert first.headers["etag"] == second.headers["etag"]
    again = client.get("/api/terms/kut", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304


def test_an_anonymous_reader_gets_a_summary_built_from_stored_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FakeTermStore({"kut": kut_term()}, stored=golden_claims())
    response = anonymous(monkeypatch, store).get("/api/terms/kut")
    assert (response.status_code, response.headers["cache-control"]) == (200, "public, max-age=300")
    assert response.json() == golden_term()
    assert (store.calls["write_back"], store.calls["remember"]) == (0, 0)


@pytest.mark.parametrize(
    ("stored", "language"), [(False, "en"), (True, "hi")], ids=["needs research", "needs a translation"]
)
def test_an_anonymous_reader_never_starts_research_or_a_translation(
    monkeypatch: pytest.MonkeyPatch, stored: bool, language: str
) -> None:
    store = FakeTermStore({"kut": kut_term()}, stored=golden_claims() if stored else StoredClaims())
    response = anonymous(monkeypatch, store).get("/api/terms/kut", params={"language": language})
    assert (response.status_code, response.json()) == (401, {"detail": NEEDS_LOOKUP_MESSAGE})
    assert (store.calls["write_back"], store.calls["remember"]) == (0, 0)


def test_an_anonymous_reader_gets_a_kept_translation_and_an_unknown_term_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kept = Term.model_validate({**golden_term(), "language": "hi"})
    store = FakeTermStore({"kut": kut_term()}, cache={(KUT_ID, "hi"): kept})
    client = anonymous(monkeypatch, store)
    assert client.get("/api/terms/kut", params={"language": "hi"}).json() == kept.model_dump(
        mode="json", by_alias=True
    )
    assert client.get("/api/terms/not-a-term").status_code == 404


def test_a_term_answers_its_cited_summary() -> None:
    response = signed_in("STUDENT").get("/api/terms/kut", params={"language": "en"})
    assert response.status_code == 200
    assert response.json() == golden_term()


def test_an_unknown_term_or_a_term_with_no_cited_summary_is_not_found() -> None:
    client = signed_in("STUDENT", FakeTermStore({"kut": kut_term()}))
    assert client.get("/api/terms/kut").status_code == 404
    assert client.get("/api/terms/not-a-term").status_code == 404


def test_an_unknown_language_is_refused() -> None:
    assert signed_in("STUDENT").get("/api/terms/kut", params={"language": "xx"}).status_code == 422


def test_lookups_are_throttled_except_for_master_admins() -> None:
    researcher = signed_in("RESEARCHER")
    answered = [researcher.get("/api/terms/kut").status_code for _ in range(61)]
    assert answered[:60] == [200] * 60
    assert answered[60] == 429
    master = signed_in("MASTER_ADMIN")
    assert {master.get("/api/terms/kut").status_code for _ in range(61)} == {200}


def test_the_summary_schema_uses_only_keywords_every_route_accepts() -> None:
    def walk(node: dict) -> None:
        assert set(node) <= SCHEMA_KEYWORDS, set(node) - SCHEMA_KEYWORDS
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert node["required"] == list(node["properties"])
            for child in node["properties"].values():
                walk(child)
        if node.get("type") == "array":
            walk(node["items"])

    walk(term_summary_schema())
