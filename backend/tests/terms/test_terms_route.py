import uuid

from fastapi.testclient import TestClient

from app.api.routes import terms
from app.composer.term_summary import term_summary_schema
from app.core.deps import get_current_user
from app.main import create_app
from app.models import User
from app.services.term_summaries import TermLookup

from ..answering.fakes import translation
from .fakes import CHECKED_AT, FakeResearch, FakeTermStore, golden_claims, golden_term, kut_term

SCHEMA_KEYWORDS = {"type", "properties", "required", "additionalProperties", "items"}


def signed_in(role: str, store: FakeTermStore | None = None) -> TestClient:
    app = create_app()
    user = User(id=uuid.UUID(int=8), name="Ravi", email="ravi@example.com", role=role)
    kept = store or FakeTermStore({"kut": kut_term()}, stored=golden_claims())
    lookup = TermLookup(
        store=kept, research=FakeResearch(None), translation=translation(), clock=lambda: CHECKED_AT
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[terms.term_lookup] = lambda: lookup
    return TestClient(app)


def test_terms_need_a_session() -> None:
    assert TestClient(create_app()).get("/api/terms/kut").status_code == 401


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
