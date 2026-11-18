import re
import uuid
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient

from app.api.public_deps import THROTTLED_DETAIL
from app.api.voice_deps import voice_call_enabled
from app.core import rate_limit
from app.core.db import get_session
from app.core.deps import SIGN_IN_DETAIL, get_current_user_any_step, get_optional_user
from app.core.http_cache import PRIVATE_NO_CACHE, PUBLIC_READ_CACHE
from app.core.rate_limit import PUBLIC_READS_PER_WINDOW
from app.main import create_app
from app.models import User

from ..readers import sign_in_as
from .stored_reads import AJRAKH, BAGRU, OUTLET, Asked, stored_reads

SUMMARY = "/api/public/summary"
PUBLIC_READS = (
    "/api/crafts/catalogue",
    f"/api/crafts/{AJRAKH}/page",
    f"/api/crafts/{AJRAKH}/process",
    f"/api/crafts/{AJRAKH}/region",
    f"/api/crafts/{AJRAKH}/shared-science",
    f"/api/shared-science/alum?craft={AJRAKH}",
    f"/api/compare?crafts={AJRAKH}&crafts={BAGRU}",
    "/api/map/crafts",
    "/api/map/layers",
    "/api/map/layers/soil-ph-0-5cm",
    "/api/map/districts/449",
    f"/api/rivers/{OUTLET}",
    "/api/molecules/6293/conformer",
    "/api/terms/kut",
    SUMMARY,
)
PUBLIC_ROUTES = {
    ("GET", "/api/categories"),
    ("GET", "/api/categories/{slug}"),
    ("GET", "/api/crafts/catalogue"),
    ("GET", "/api/crafts/{slug}/page"),
    ("GET", "/api/crafts/{slug}/process"),
    ("GET", "/api/crafts/{slug}/region"),
    ("GET", "/api/crafts/{slug}/shared-science"),
    ("GET", "/api/shared-science/{term_key}"),
    ("GET", "/api/compare"),
    ("GET", "/api/map/crafts"),
    ("GET", "/api/map/layers"),
    ("GET", "/api/map/layers/{layer}"),
    ("GET", "/api/map/districts/{district_lgd}"),
    ("GET", "/api/rivers/{main_riv}"),
    ("GET", "/api/molecules/{pubchem_cid}/conformer"),
    ("GET", "/api/terms/{key}"),
    ("GET", SUMMARY),
}
SIGN_IN_FLOW = {
    ("GET", "/health"),
    ("GET", "/health/ready"),
    ("GET", "/api/auth/config"),
    ("GET", "/api/auth/set-password"),
    ("GET", "/api/privacy/notice"),
    ("POST", "/api/auth/forgot-password"),
    ("POST", "/api/auth/google/nonce"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/auth/oidc/nonce"),
    ("POST", "/api/auth/set-password"),
    ("POST", "/api/auth/set-password/check"),
    ("POST", "/api/auth/signup"),
    ("POST", "/api/auth/two-factor/verify"),
    ("POST", "/api/voice/llm/v1/chat/completions"),
}
CLAIM_READS = {
    f"/api/crafts/{AJRAKH}/page": "craft_page_records",
    f"/api/crafts/{AJRAKH}/process": "process_records",
    f"/api/crafts/{AJRAKH}/shared-science": "craft_shared_science",
    f"/api/shared-science/alum?craft={AJRAKH}": "shared_concept_of",
    f"/api/compare?crafts={AJRAKH}&crafts={BAGRU}": "craft_comparison",
    "/api/map/districts/449": "district_records",
    "/api/terms/kut": "term_lookup",
}
READER_KEYS = ("email", "userId", "askedBy", "createdById", "ipHash", "passwordHash", "accessToken")
SUMMARY_CACHE = "public, max-age=86400"
STUDENT = User(id=uuid.UUID(int=7), name="Asha", email="asha@example.com", role="STUDENT")
RESEARCHER = User(id=uuid.UUID(int=8), name="Ravi", email="ravi@example.com", role="RESEARCHER")


async def no_session() -> Any:
    yield None


def _routes() -> dict[tuple[str, str], set[Any]]:
    return dict(_routes_at_import())


def _routes_at_import() -> list[tuple[tuple[str, str], set[Any]]]:
    found: list[tuple[tuple[str, str], set[Any]]] = []
    for route in iter_route_contexts(create_app().routes):
        if route.dependant is None:
            continue
        calls = _calls(route.dependant)
        found.extend(((method, route.path), calls) for method in sorted(route.methods or ()))
    return found


def _calls(dependant: Any) -> set[Any]:
    calls: set[Any] = set()
    for sub in dependant.dependencies:
        calls.add(sub.call)
        calls |= _calls(sub)
    return calls


def _keys(body: Any) -> set[str]:
    if isinstance(body, dict):
        return set(body) | {key for value in body.values() for key in _keys(value)}
    if isinstance(body, list):
        return {key for value in body for key in _keys(value)}
    return set()


@pytest.fixture
def stored(monkeypatch: pytest.MonkeyPatch) -> Asked:
    asked = Asked()
    for module, names in stored_reads(asked).items():
        for name, value in names.items():
            monkeypatch.setattr(module, name, value)
    return asked


def reader_client(reader: User | None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_session] = no_session
    if reader is not None:
        sign_in_as(app, lambda: reader)
    return TestClient(app)


def shown(response: httpx.Response) -> Any:
    return (
        response.json() if response.headers["content-type"].startswith("application/json") else response.text
    )


@pytest.mark.usefixtures("stored")
@pytest.mark.parametrize("path", PUBLIC_READS)
def test_an_anonymous_reader_gets_exactly_what_a_student_gets(path: str) -> None:
    anonymous = reader_client(None).get(path)
    student = reader_client(STUDENT).get(path)
    assert (anonymous.status_code, student.status_code) == (200, 200), path
    assert shown(anonymous) == shown(student)
    assert not set(READER_KEYS) & _keys(shown(anonymous))


@pytest.mark.usefixtures("stored")
@pytest.mark.parametrize("path", PUBLIC_READS)
def test_anonymous_reads_are_public_short_lived_and_revalidated(path: str) -> None:
    client = reader_client(None)
    first = client.get(path)
    assert first.headers["cache-control"] == (SUMMARY_CACHE if path == SUMMARY else PUBLIC_READ_CACHE)
    if path != SUMMARY:
        assert "Authorization" in first.headers["vary"]
    again = client.get(path, headers={"If-None-Match": first.headers["etag"]})
    assert (again.status_code, again.content) == (304, b"")


@pytest.mark.usefixtures("stored")
@pytest.mark.parametrize("path", [path for path in PUBLIC_READS if path != SUMMARY])
def test_signed_in_reads_stay_private(path: str) -> None:
    response = reader_client(STUDENT).get(path)
    assert response.headers["cache-control"] == PRIVATE_NO_CACHE
    assert "Authorization" in response.headers["vary"]


@pytest.mark.parametrize(
    ("reader", "acls"),
    [(None, ("PUBLIC",)), (STUDENT, ("PUBLIC",)), (RESEARCHER, ("PUBLIC", "RESEARCHER"))],
    ids=["anonymous", "student", "researcher"],
)
def test_every_public_read_of_claims_is_built_for_the_chunks_its_reader_may_quote(
    stored: Asked, reader: User | None, acls: tuple[str, ...]
) -> None:
    client = reader_client(reader)
    for path in CLAIM_READS:
        assert client.get(path).status_code == 200, path
    assert stored.acls == {name: {acls} for name in CLAIM_READS.values()}


@pytest.mark.usefixtures("stored")
def test_an_anonymous_craft_page_holds_no_evidence_a_researcher_still_sees() -> None:
    path = f"/api/crafts/{AJRAKH}/page"
    anonymous = reader_client(None).get(path).json()
    researcher = reader_client(RESEARCHER).get(path).json()
    assert anonymous["evidence"] is None and researcher["evidence"] is not None
    assert {claim["id"] for claim in anonymous["claims"]} < {claim["id"] for claim in researcher["claims"]}


@pytest.mark.usefixtures("stored")
def test_the_full_craft_list_is_refused_to_an_anonymous_reader() -> None:
    response = reader_client(None).get("/api/crafts/catalogue", params={"includeInactive": "true"})
    assert (response.status_code, response.json()) == (401, {"detail": SIGN_IN_DETAIL})
    listed = reader_client(None).get("/api/crafts/catalogue").json()["crafts"]
    assert not {"status", "mergedIntoId", "referenceCount"} & {key for row in listed for key in row}


def test_every_route_open_without_a_session_is_a_listed_public_read_or_the_sign_in_flow() -> None:
    routes = _routes()
    open_routes = {route for route, calls in routes.items() if get_current_user_any_step not in calls}
    assert open_routes == PUBLIC_ROUTES | SIGN_IN_FLOW
    assert {route for route, calls in routes.items() if get_optional_user in calls} == PUBLIC_ROUTES


@pytest.mark.parametrize(
    "route", sorted(route for route, calls in _routes_at_import() if get_current_user_any_step in calls)
)
def test_every_other_route_still_needs_a_session(route: tuple[str, str]) -> None:
    method, path = route
    app = create_app()
    app.dependency_overrides[voice_call_enabled] = lambda: True
    response = TestClient(app).request(method, re.sub(r"\{[^}]+\}", "1", path), json={})
    assert response.status_code == 401, route


@pytest.mark.usefixtures("stored")
def test_anonymous_reads_are_limited_per_address_and_signed_in_reads_are_not() -> None:
    anonymous = reader_client(None)
    answered = [anonymous.get("/api/map/crafts").status_code for _ in range(PUBLIC_READS_PER_WINDOW)]
    assert set(answered) == {200}
    refused = anonymous.get("/api/map/crafts")
    assert (refused.status_code, refused.json()) == (429, {"detail": THROTTLED_DETAIL})
    assert int(refused.headers["retry-after"]) >= 1
    assert reader_client(STUDENT).get("/api/map/crafts").status_code == 200


def test_the_limit_counts_each_address_on_its_own() -> None:
    def visitor(address: str) -> Any:
        return SimpleNamespace(client=SimpleNamespace(host=address), headers={})

    first, second = visitor("203.0.113.5"), visitor("198.51.100.7")
    assert all(rate_limit.public_read_attempt(first)[0] for _ in range(PUBLIC_READS_PER_WINDOW))
    assert rate_limit.public_read_attempt(first)[0] is False
    assert rate_limit.public_read_attempt(second)[0] is True
