import io
import json
import uuid
import wave
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import voice_deps
from app.api.routes import voice as voice_routes
from app.core.deps import get_current_user
from app.main import create_app
from app.models import User
from app.schemas.voice import RelaySessionStarted, VoiceTranscript
from app.schemas.voice_llm import VOICE_LLM_PATH, LlmError
from app.voice.notice import VOICE_NOTICE_VERSION, voice_notice_sha256
from app.voice.runtime import VoiceRuntime, VoiceSettings

from ..contracts.golden import golden_json
from .fakes import (
    ALUM,
    BEARER,
    CONVERSATION_ID,
    CRAFT,
    HMAC_KEY,
    SESSION_ID,
    USER_ID,
    MemoryStore,
    agent_session,
    cipher,
    session,
)

FIXTURES = Path(__file__).parent / "fixtures"
NOTICE_SHA256 = "f4284511228c9cc6bafd2c530376d9c2033c9d2497dc6cdc8fc0391ef1dbef0a"
REPLY_AUDIO = b"\xff\xfb" * 48_000


def wav(seconds: float) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(1)
        out.setframerate(8_000)
        out.writeframes(b"\x80" * int(seconds * 8_000))
    return buffer.getvalue()


def elevenlabs_answer(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v1/speech-to-text":
        return httpx.Response(200, content=(FIXTURES / "speech_to_text.json").read_bytes())
    if request.url.path.startswith("/v1/text-to-speech/"):
        return httpx.Response(200, content=REPLY_AUDIO)
    return httpx.Response(200, json={})


def settings(transport: str = "RELAY") -> VoiceSettings:
    return VoiceSettings(
        transport=transport,
        max_live_sessions=5,
        voice_id="voice_1",
        api_key="test-only-elevenlabs-key",
        agent_id="agent_test",
        llm_bearer=BEARER,
        hmac_key=HMAC_KEY,
        cipher=cipher(),
    )


class Client:
    def __init__(self, store: MemoryStore, *, transport: str = "RELAY", user: User | None = None) -> None:
        app = create_app()
        runtime = VoiceRuntime(client=httpx.AsyncClient(transport=httpx.MockTransport(elevenlabs_answer)))
        learner = user or User(
            id=USER_ID,
            name="Meera Rao",
            email="meera@example.org",
            role="STUDENT",
            emailVerifiedAt=datetime.now(UTC),
        )
        app.dependency_overrides[voice_deps.voice_store] = lambda: store
        app.dependency_overrides[voice_deps.current_voice] = lambda: settings(transport)
        app.dependency_overrides[voice_deps.voice_runtime] = lambda: runtime
        app.dependency_overrides[get_current_user] = lambda: learner
        self.http = TestClient(app)


@pytest.fixture
def now() -> Iterator[datetime]:
    yield datetime.now(UTC)


def live_agent_store(now: datetime, **changes: object) -> MemoryStore:
    store = MemoryStore(used_before=60)
    record = agent_session(
        started_at=now - timedelta(seconds=20), expires_at=now + timedelta(seconds=100), **changes
    )
    store.sessions[record.id] = record
    return store


def llm_post(
    client: Client,
    *,
    conversation: str = CONVERSATION_ID,
    bearer: str | None = BEARER,
    body: dict | None = None,
) -> httpx.Response:
    headers = {"X-KV-Conversation-Id": conversation}
    if bearer is not None:
        headers["Authorization"] = f"Bearer {bearer}"
    return client.http.post(
        VOICE_LLM_PATH, headers=headers, json=body or golden_json("voice.llm-request.golden.json")
    )


@pytest.mark.parametrize("case", ["forged conversation id", "forged nonce", "reused nonce", "missing bearer"])
def test_the_custom_llm_refuses_every_unbound_call_with_one_401(case: str, now: datetime) -> None:
    store = live_agent_store(now)
    record = store.sessions[SESSION_ID]
    conversation, bearer = CONVERSATION_ID, BEARER
    if case == "forged conversation id":
        conversation = "conv_forged"
    elif case == "forged nonce":
        store.sessions[SESSION_ID] = replace(record, nonce_hash="0" * 64)
    elif case == "reused nonce":
        store.sessions[SESSION_ID] = replace(record, conversation_id="conv_second")
        conversation = "conv_second"
    else:
        bearer = None
    response = llm_post(Client(store, transport="AGENT"), conversation=conversation, bearer=bearer)
    assert response.status_code == 401
    error = LlmError.model_validate(response.json()).error
    assert (error.code, error.message) == ("unauthorized", "This voice session is not allowed.")


def test_a_bound_call_streams_a_cited_reply(now: datetime) -> None:
    store = live_agent_store(now, mode="VERIFIED")
    response = llm_post(Client(store, transport="AGENT"))
    assert response.status_code == 200 and response.headers["content-type"].startswith("text/event-stream")
    assert ALUM in response.text and response.text.endswith("data: [DONE]\n\n")
    assert store.sessions[SESSION_ID].turn_count == 1


def test_a_bound_call_that_does_not_stream_is_a_bad_request(now: datetime) -> None:
    body = {**golden_json("voice.llm-request.golden.json"), "stream": False}
    response = llm_post(Client(live_agent_store(now), transport="AGENT"), body=body)
    assert response.status_code == 400 and response.json()["error"]["code"] == "bad_request"


def test_starting_without_the_notice_names_its_version() -> None:
    response = Client(MemoryStore()).http.post("/api/voice/session", json={"craftSlug": CRAFT.slug})
    assert response.status_code == 403
    assert response.headers["x-voice-consent-required"] == VOICE_NOTICE_VERSION


def test_a_day_without_seconds_left_is_429_until_midnight() -> None:
    store = MemoryStore(used_before=600)
    store.consents.add((USER_ID, VOICE_NOTICE_VERSION))
    response = Client(store).http.post("/api/voice/session", json={"craftSlug": CRAFT.slug})
    assert response.status_code == 429 and int(response.headers["retry-after"]) > 0


def test_a_relay_call_starts_takes_a_turn_and_keeps_its_transcript() -> None:
    store = MemoryStore(used_before=60)
    store.consents.add((USER_ID, VOICE_NOTICE_VERSION))
    client = Client(store)
    started = client.http.post("/api/voice/session", json={"craftSlug": CRAFT.slug, "mode": "VERIFIED"})
    assert started.status_code == 201
    session_id = RelaySessionStarted.model_validate(started.json()).voice_session_id
    files = {"audio": ("KalaVigyan_Voice-Session.webm", b"recorded", "audio/webm")}
    turn = client.http.post(f"/api/voice/session/{session_id}/turns", files=files)
    assert turn.status_code == 200 and "event: done" in turn.text
    transcript = VoiceTranscript.model_validate(
        client.http.get(f"/api/voice/session/{session_id}/transcript").json()
    )
    [spoken] = transcript.turns
    assert spoken.sentences[0].text == ALUM
    speech = client.http.get(f"/api/voice/session/{session_id}/turns/{spoken.turn_id}/speech")
    assert speech.status_code == 200 and speech.headers["content-type"] == "audio/mpeg"
    assert speech.content == REPLY_AUDIO


def test_a_recording_off_the_contract_is_refused(now: datetime) -> None:
    store = MemoryStore()
    store.sessions[SESSION_ID] = session(started_at=now, expires_at=now + timedelta(seconds=60))
    client = Client(store)
    path = f"/api/voice/session/{SESSION_ID}/turns"
    wrong = client.http.post(path, files={"audio": ("a.mp3", b"x", "audio/mpeg")})
    assert wrong.status_code == 415
    huge = client.http.post(path, files={"audio": ("a.webm", b"x" * (4 * 1024 * 1024 + 1), "audio/webm")})
    assert huge.status_code == 413
    past_a_minute = client.http.post(path, files={"audio": ("a.webm", b"x" * 300_001, "audio/webm")})
    assert past_a_minute.status_code == 413
    long_wav = client.http.post(path, files={"audio": ("a.wav", wav(61.0), "audio/wav")})
    assert long_wav.status_code == 413
    not_wav = client.http.post(path, files={"audio": ("a.wav", b"RIFF0000WAVEjunk", "audio/wav")})
    assert not_wav.status_code == 400
    assert store.sessions[SESSION_ID].turn_count == 0 and store.ledger == {}


def test_turns_past_forty_in_ten_minutes_are_throttled(now: datetime) -> None:
    store = MemoryStore()
    store.sessions[SESSION_ID] = session(started_at=now, expires_at=now + timedelta(seconds=60))
    client = Client(store)
    path = f"/api/voice/session/{SESSION_ID}/turns"
    for _ in range(40):
        assert client.http.post(path, files={"audio": ("a.mp3", b"x", "audio/mpeg")}).status_code == 415
    throttled = client.http.post(path, files={"audio": ("a.webm", b"x", "audio/webm")})
    assert throttled.status_code == 429 and int(throttled.headers["retry-after"]) > 0


def test_a_reply_cannot_be_fetched_after_the_call_and_its_grace(now: datetime) -> None:
    store = MemoryStore()
    store.sessions[SESSION_ID] = session(
        started_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(minutes=8),
        ended_at=now - timedelta(minutes=3),
    )
    response = Client(store).http.get(f"/api/voice/session/{SESSION_ID}/turns/{uuid.uuid4()}/speech")
    assert response.status_code == 410


def test_another_user_s_call_is_not_found(now: datetime) -> None:
    store = MemoryStore()
    store.sessions[SESSION_ID] = session(
        user_id=uuid.uuid4(), started_at=now, expires_at=now + timedelta(seconds=60)
    )
    client = Client(store)
    assert client.http.get(f"/api/voice/session/{SESSION_ID}/transcript").status_code == 404
    assert client.http.post(f"/api/voice/session/{SESSION_ID}/end").status_code == 404


def test_a_transcript_past_its_retention_is_gone(now: datetime) -> None:
    store = MemoryStore()
    store.sessions[SESSION_ID] = session(
        ended_at=now - timedelta(days=31), retention_until=now - timedelta(days=1)
    )
    assert Client(store).http.get(f"/api/voice/session/{SESSION_ID}/transcript").status_code == 404


def test_the_voice_notice_is_served_with_its_version() -> None:
    body = Client(MemoryStore()).http.get("/api/voice/notice").json()
    assert body["version"] == VOICE_NOTICE_VERSION and body["title"] == "Voice notice"
    assert "{contact}" not in body["body"]
    assert voice_notice_sha256() == NOTICE_SHA256, (
        "the notice changed: bump VOICE_NOTICE_VERSION and this hash"
    )


def test_the_answer_config_carries_voice_availability() -> None:
    voice = Client(MemoryStore(used_before=60)).http.get("/api/answers/config").json()["voice"]
    assert voice["configured"] is True and voice["transport"] == "RELAY" and voice["remainingSeconds"] == 540


def test_the_voice_routes_live_under_the_api_prefix() -> None:
    paths = {route.path for route in voice_routes.router.routes}
    assert "/voice/llm/v1/chat/completions" in paths and json.dumps(sorted(paths))
