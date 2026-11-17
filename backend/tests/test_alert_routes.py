import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.routes import explainers, notifications, saved_explainers
from app.core.db import get_session
from app.core.deps import get_current_user
from app.main import create_app
from app.models import User
from app.services.explainer_history import UnknownExplainer
from app.services.saved_explainers import SavedFull

READER = uuid.UUID(int=7)
OWN_NOTE = uuid.UUID(int=11)
EXPLAINER = uuid.UUID(int=21)


class QuietSession:
    async def commit(self) -> None:
        return None


def client() -> TestClient:
    app = create_app()
    user = User(id=READER, name="Meera Rao", email="meera@example.org", role="STUDENT")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = QuietSession
    return TestClient(app)


def test_a_note_is_marked_read_only_for_the_signed_in_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[uuid.UUID] = []

    async def mark_read(session: Any, user_id: uuid.UUID, note_id: uuid.UUID) -> bool:
        asked.append(user_id)
        return note_id == OWN_NOTE

    monkeypatch.setattr(notifications, "mark_read", mark_read)
    http = client()
    assert http.post(f"/api/notifications/{OWN_NOTE}/read").status_code == 204
    assert http.post(f"/api/notifications/{uuid.uuid4()}/read").status_code == 404
    assert asked == [READER, READER]


@pytest.mark.parametrize(
    ("refusal", "status"), [(UnknownExplainer(EXPLAINER), 404), (SavedFull("full"), 409)]
)
def test_saving_refuses_another_reader_s_explainer_and_a_full_list(
    monkeypatch: pytest.MonkeyPatch, refusal: Exception, status: int
) -> None:
    async def save_explainer(session: Any, user_id: uuid.UUID, explainer_id: uuid.UUID) -> Any:
        assert (user_id, explainer_id) == (READER, EXPLAINER)
        raise refusal

    monkeypatch.setattr(saved_explainers, "save_explainer", save_explainer)
    assert client().put(f"/api/saved-explainers/{EXPLAINER}").status_code == status


def test_an_explainer_is_not_found_for_anyone_but_its_asker(monkeypatch: pytest.MonkeyPatch) -> None:
    async def latest_version(session: Any, explainer_id: uuid.UUID, user_id: uuid.UUID) -> Any:
        assert user_id == READER
        raise UnknownExplainer(explainer_id)

    monkeypatch.setattr(explainers, "latest_version", latest_version)
    http = client()
    assert http.get(f"/api/explainers/{EXPLAINER}").status_code == 404
    assert http.get(f"/api/explainers/{EXPLAINER}/versions/0").status_code == 422
    assert http.get("/api/explainers/not-a-uuid/versions").status_code == 422
