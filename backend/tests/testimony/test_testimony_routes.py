import uuid
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
from fastapi import FastAPI

from app.api.routes import artisan_contributions, testimony_review
from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import ArtisanProfile, User

from . import fakes


def person(role: str, user_id: uuid.UUID = fakes.USER) -> User:
    return User(
        id=user_id, email=f"{role.lower()}@example.org", name="Bilal Khatri", role=role, twoFactorEnabled=True
    )


@pytest.fixture
def state() -> dict[str, object]:
    return {}


@pytest.fixture
def app(state: dict[str, object]) -> Iterator[FastAPI]:
    built = FastAPI()
    built.include_router(testimony_review.router, prefix="/api")
    built.include_router(artisan_contributions.router, prefix="/api")

    async def session() -> AsyncIterator[object]:
        yield state["session"]

    built.dependency_overrides[get_session] = session
    built.dependency_overrides[get_current_user] = lambda: state["user"]
    yield built


async def call(app: FastAPI, method: str, path: str, **options: object) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **options)


async def test_the_review_queue_is_refused_to_artisans_and_researchers(
    app: FastAPI, state: dict[str, object]
) -> None:
    state["session"] = fakes.FakeSession()
    for role in ("STUDENT", "ARTISAN", "RESEARCHER"):
        state["user"] = person(role)
        response = await call(app, "GET", "/api/testimony/review")
        assert response.status_code == 403, role
        assert response.json() == {
            "detail": "Reviewing artisans' contributions is for professors and admins."
        }


async def test_a_stale_version_is_refused_with_the_reload_sentence(
    app: FastAPI, state: dict[str, object]
) -> None:
    item = fakes.contribution(version=3)
    state["user"], state["session"] = person("PROFESSOR", fakes.REVIEWER), fakes.session_for(item)
    response = await call(app, "POST", f"/api/testimony/review/{item.id}/approve", json={"version": 2})
    assert response.status_code == 409
    assert response.json() == {"detail": "Someone changed this contribution. Reload it."}


async def test_a_held_back_name_blocks_approval_and_names_the_problem(
    app: FastAPI, state: dict[str, object]
) -> None:
    item = fakes.contribution(english="Khatri and I wash the cloth after the alum")
    session = fakes.session_for(item)
    session.rows[(User, fakes.USER)] = person("ARTISAN")
    session.rows[(ArtisanProfile, fakes.USER)] = fakes.profile(
        creditMode="FIRST_NAME", creditShortName="Bilal"
    )
    state["user"], state["session"] = person("PROFESSOR", fakes.REVIEWER), session
    response = await call(app, "POST", f"/api/testimony/review/{item.id}/approve", json={"version": 2})
    assert response.status_code == 422
    assert response.json()["problems"] == [
        "a held-back name is in the quote, the English or the claim; edit it out first"
    ]
    assert item.status == "PENDING"


async def test_a_quote_not_in_english_needs_its_english_before_approval(
    app: FastAPI, state: dict[str, object]
) -> None:
    item = fakes.contribution(english=None)
    state["user"], state["session"] = person("ADMIN", fakes.REVIEWER), fakes.session_for(item)
    response = await call(app, "POST", f"/api/testimony/review/{item.id}/approve", json={"version": 2})
    assert response.status_code == 422
    assert response.json()["problems"] == ["a quote not in English needs its English"]


async def test_a_rejection_of_other_needs_a_note(app: FastAPI, state: dict[str, object]) -> None:
    item = fakes.contribution()
    state["user"], state["session"] = person("PROFESSOR", fakes.REVIEWER), fakes.session_for(item)
    response = await call(
        app, "POST", f"/api/testimony/review/{item.id}/reject", json={"version": 2, "reason": "OTHER"}
    )
    assert response.status_code == 422
    assert response.json()["problems"] == ["a reason of OTHER needs a note"]


async def test_unknown_fields_are_refused_in_a_review_body(app: FastAPI, state: dict[str, object]) -> None:
    item = fakes.contribution()
    state["user"], state["session"] = person("PROFESSOR", fakes.REVIEWER), fakes.session_for(item)
    body = {"version": 2, "level": "VERIFIED"}
    response = await call(app, "POST", f"/api/testimony/review/{item.id}/approve", json=body)
    assert response.status_code == 422


@pytest.mark.parametrize("final", ["REJECTED", "WITHDRAWN"])
async def test_a_final_contribution_cannot_be_taken_back(
    app: FastAPI, state: dict[str, object], final: str
) -> None:
    item = fakes.contribution(
        status=final, rejectReason="UNCLEAR", rejectedAt=fakes.at(8), withdrawnAt=fakes.at(8)
    )
    state["user"], state["session"] = person("ARTISAN"), fakes.session_for(item)
    response = await call(app, "POST", f"/api/artisan/contributions/{item.id}/withdraw")
    assert response.status_code == 409
    assert state["session"].rolled_back


async def test_another_accounts_contribution_is_not_found(app: FastAPI, state: dict[str, object]) -> None:
    item = fakes.contribution()
    state["user"], state["session"] = person("ARTISAN", fakes.OTHER_USER), fakes.session_for(item)
    for method, path in (
        ("POST", f"/api/artisan/contributions/{item.id}/withdraw"),
        ("GET", f"/api/artisan/contributions/{item.id}/audio"),
        ("GET", f"/api/artisan/conversations/{fakes.CONVERSATION}"),
        ("DELETE", f"/api/artisan/conversations/{fakes.CONVERSATION}"),
    ):
        response = await call(app, method, path)
        assert response.status_code == 404, path


async def test_withdrawing_needs_no_capability_only_ownership(app: FastAPI, state: dict[str, object]) -> None:
    item = fakes.contribution(status="REJECTED", rejectReason="UNCLEAR", rejectedAt=fakes.at(8))
    state["user"], state["session"] = person("STUDENT"), fakes.session_for(item)
    response = await call(app, "POST", f"/api/artisan/contributions/{item.id}/withdraw")
    assert response.status_code == 409
