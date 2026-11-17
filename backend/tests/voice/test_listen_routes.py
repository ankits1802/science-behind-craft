import uuid
from dataclasses import dataclass, field
from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import listen_deps
from app.api.routes import knowledge
from app.core.deps import get_current_user
from app.main import create_app
from app.models import User
from app.providers.quota import LedgerEntry
from app.research.explainer import Explainer
from app.schemas.listen import ListenScript
from app.voice.availability import HIDDEN_VOICE
from app.voice.listen import ListenHold
from app.voice.runtime import VoiceRuntime, VoiceSettings

from .listen_fakes import LEARNER, VOICE_ID, MemoryLedger, MemoryObjects, Narrations, golden_explainer

ANSWER = golden_explainer().answer_id
PATH = f"/api/answers/{ANSWER}/listen"
LANGUAGES = ["en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "or", "pa", "as", "ur"]


@dataclass
class MemoryListenStore:
    explainers: dict[tuple[uuid.UUID, uuid.UUID], Explainer] = field(default_factory=dict)
    ledger: MemoryLedger = field(default_factory=MemoryLedger)

    async def explainer(self, answer_id: uuid.UUID, user_id: uuid.UUID) -> Explainer | None:
        return self.explainers.get((answer_id, user_id))

    async def hold(self, entry: LedgerEntry, now: datetime) -> ListenHold:
        return await self.ledger.hold(entry, now)

    async def record(self, entry: LedgerEntry) -> None:
        await self.ledger.record(entry)


class Client:
    def __init__(
        self, *, role: str = "STUDENT", ledger: MemoryLedger | None = None, failing: str | None = None
    ):
        app = create_app()
        self.store = MemoryListenStore(ledger=ledger or MemoryLedger())
        self.store.explainers[(ANSWER, LEARNER)] = golden_explainer()
        self.narrator = Narrations(failing=failing)
        tools = listen_deps.ListenTools(objects=MemoryObjects(), narrator=self.narrator, voice_id=VOICE_ID)
        user = User(id=LEARNER, name="Meera Rao", email="meera@example.org", role=role)
        app.dependency_overrides[get_current_user] = lambda: user
        app.dependency_overrides[listen_deps.listen_store] = lambda: self.store
        app.dependency_overrides[listen_deps.listen_tools] = lambda: tools
        self.http = TestClient(app)


def test_the_reader_s_own_explainer_is_read_aloud_with_its_timings() -> None:
    response = Client().http.get(PATH, params={"language": "en"})
    assert response.status_code == 200
    script = ListenScript.model_validate(response.json())
    assert (script.answer_id, script.language) == (ANSWER, "en")
    assert [track.block_id for track in script.tracks] == ["s1.b1", "s2.b1", "s3.b1"]


def test_one_section_can_be_read_alone() -> None:
    client = Client()
    response = client.http.get(PATH, params={"section": "s2"})
    assert [track["blockId"] for track in response.json()["tracks"]] == ["s2.b1"]
    assert len(client.narrator.calls) == 1


@pytest.mark.parametrize(
    ("path", "params", "status"),
    [
        (PATH, {"language": "hi"}, 404),
        (f"/api/answers/{uuid.UUID(int=5)}/listen", {}, 404),
        (PATH, {"section": "s9"}, 404),
        (PATH, {"section": "intro"}, 422),
        (PATH, {"language": "es"}, 422),
    ],
    ids=[
        "another language",
        "someone else's answer",
        "unknown section",
        "malformed section",
        "unknown language",
    ],
)
def test_nothing_to_read_is_404_and_a_malformed_ask_422(path: str, params: dict, status: int) -> None:
    client = Client()
    assert client.http.get(path, params=params).status_code == status
    assert client.narrator.calls == []


def test_no_seconds_left_is_429_until_midnight() -> None:
    response = Client(ledger=MemoryLedger(allowance=600, used=600)).http.get(PATH)
    assert response.status_code == 429 and int(response.headers["retry-after"]) > 0
    assert response.json()["detail"] == "Not enough listening time is left today."


def test_a_provider_failure_is_503_without_its_details() -> None:
    response = Client(failing="Presence of iron").http.get(PATH)
    assert response.status_code == 503
    assert response.json()["detail"] == "Listening isn't available right now. Try again later."


def test_listen_is_limited_to_thirty_presses_in_ten_minutes_except_for_a_master_admin() -> None:
    student, master = Client(), Client(role="MASTER_ADMIN", ledger=MemoryLedger(allowance=None))
    assert {student.http.get(PATH, params={"section": "s2"}).status_code for _ in range(30)} == {200}
    assert student.http.get(PATH, params={"section": "s2"}).status_code == 429
    assert {master.http.get(PATH, params={"section": "s2"}).status_code for _ in range(31)} == {200}


def config_client(
    monkeypatch: pytest.MonkeyPatch, *, bucket: bool, key: str | None, role: str = "STUDENT"
) -> TestClient:
    async def voice() -> VoiceSettings:
        return VoiceSettings(
            transport="RELAY",
            max_live_sessions=5,
            voice_id=VOICE_ID,
            api_key=key,
            agent_id=None,
            llm_bearer=None,
            hmac_key=None,
            cipher=None,
        )

    monkeypatch.setattr(listen_deps, "media_bucket", lambda: MemoryObjects() if bucket else None)
    monkeypatch.setattr(listen_deps, "current_voice", voice)
    app = create_app()
    app.state.voice_runtime = VoiceRuntime(
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    )
    user = User(id=LEARNER, name="Meera Rao", email="meera@example.org", role=role)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[knowledge.offered_voice] = lambda: dict(HIDDEN_VOICE)
    return TestClient(app)


def test_the_config_offers_listen_in_every_answer_language_when_it_can_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = (
        config_client(monkeypatch, bucket=True, key="test-only-elevenlabs-key")
        .get("/api/answers/config")
        .json()
    )
    assert body["listen"] == {"languages": LANGUAGES}


@pytest.mark.parametrize(
    ("bucket", "key", "role"),
    [
        (False, "test-only-elevenlabs-key", "STUDENT"),
        (True, None, "STUDENT"),
        (True, "test-only-key", "GUEST"),
    ],
    ids=["no bucket", "no key", "unknown role"],
)
def test_the_config_hides_listen_when_it_cannot_work(
    monkeypatch: pytest.MonkeyPatch, bucket: bool, key: str | None, role: str
) -> None:
    body = config_client(monkeypatch, bucket=bucket, key=key, role=role).get("/api/answers/config").json()
    assert body["listen"] == {"languages": []}
