import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import film_deps
from app.api.routes import knowledge
from app.core.deps import get_current_user
from app.core.errors import ExternalFailure
from app.main import create_app
from app.models import User
from app.providers.media_router import MediaRouter
from app.providers.router import RouterError
from app.research.explainer import Explainer
from app.schemas.film import FilmScore
from app.voice.availability import HIDDEN_VOICE

from .listen_fakes import LEARNER, MemoryObjects, golden_explainer
from .score_fakes import MemoryMaker

ANSWER = golden_explainer().answer_id
PATH = f"/api/answers/{ANSWER}/film-score"


@dataclass
class MemoryFilmStore:
    explainers: dict[tuple[uuid.UUID, uuid.UUID], Explainer] = field(default_factory=dict)

    async def explainer(self, answer_id: uuid.UUID, user_id: uuid.UUID) -> Explainer | None:
        return self.explainers.get((answer_id, user_id))


class Client:
    def __init__(self, *, role: str = "STUDENT", maker: MemoryMaker | None = None) -> None:
        app = create_app()
        store = MemoryFilmStore()
        store.explainers[(ANSWER, LEARNER)] = golden_explainer()
        self.maker = maker or MemoryMaker()
        tools = film_deps.FilmTools(objects=MemoryObjects(), maker=self.maker)
        user = User(id=LEARNER, name="Meera Rao", email="meera@example.org", role=role)
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[film_deps.film_store] = lambda: store
        app.dependency_overrides[film_deps.film_tools] = lambda: tools
        self.http = TestClient(app)


def test_the_reader_s_own_explainer_gets_its_score_and_a_second_ask_reuses_it() -> None:
    client = Client()
    first = client.http.get(PATH, params={"language": "en"})
    assert first.status_code == 200
    score = FilmScore.model_validate(first.json())
    assert (score.answer_id, score.language, [cue.block_id for cue in score.cues]) == (
        ANSWER,
        "en",
        ["s1.b1", "s2.b1"],
    )
    assert client.http.get(PATH, params={"language": "en"}).status_code == 200
    assert len(client.maker.calls) == 3


@pytest.mark.parametrize(
    ("path", "params", "status"),
    [
        (PATH, {"language": "hi"}, 404),
        (f"/api/answers/{uuid.UUID(int=5)}/film-score", {"language": "en"}, 404),
        (PATH, {"language": "es"}, 422),
        (PATH, {}, 422),
    ],
    ids=["another language", "someone else's answer", "not an answer language", "no language"],
)
def test_only_the_asker_s_explainer_in_its_language_is_scored(path: str, params: dict, status: int) -> None:
    client = Client()
    assert client.http.get(path, params=params).status_code == status
    assert client.maker.calls == []


def test_a_refused_router_answers_503_and_keeps_no_score() -> None:
    client = Client(maker=MemoryMaker(refusing=True))
    response = client.http.get(PATH, params={"language": "en"})
    assert (response.status_code, response.json()) == (503, {"detail": film_deps.UNAVAILABLE_DETAIL})


def test_a_failing_elevenlabs_answers_503() -> None:
    class Down(MemoryMaker):
        async def generate(self, ask: Any) -> Any:
            raise ExternalFailure("ElevenLabs answered 500", kind="unavailable", service="elevenlabs")

    response = Client(maker=Down()).http.get(PATH, params={"language": "en"})
    assert response.status_code == 503


def test_more_than_ten_scores_in_ten_minutes_are_throttled_except_for_a_master_admin() -> None:
    student = Client()
    answers = [student.http.get(PATH, params={"language": "en"}).status_code for _ in range(11)]
    assert answers[:10] == [200] * 10 and answers[10] == 429
    master = Client(role="MASTER_ADMIN")
    assert {master.http.get(PATH, params={"language": "en"}).status_code for _ in range(12)} == {200}


def test_the_ask_config_offers_the_score_only_when_music_can_be_made(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client()
    client.http.app.dependency_overrides[knowledge.offered_voice] = lambda: dict(HIDDEN_VOICE)
    assert client.http.get("/api/answers/config").json()["film"] == {"score": False}

    async def available(self: MediaRouter, ask: Any) -> bool:
        return ask.task.value == "MUSIC" and ask.units == 30.0

    monkeypatch.setattr(film_deps, "media_bucket", MemoryObjects)
    monkeypatch.setattr(MediaRouter, "available", available)
    monkeypatch.setattr(film_deps, "sessionmaker", lambda: None)
    assert client.http.get("/api/answers/config").json()["film"] == {"score": True}

    async def broken(self: MediaRouter, ask: Any) -> bool:
        raise RouterError("unsupported", "no route")

    monkeypatch.setattr(MediaRouter, "available", broken)
    assert client.http.get("/api/answers/config").json()["film"] == {"score": False}
