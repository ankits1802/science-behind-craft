from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.routes import artisan_conversations as artisan_routes
from app.services.malware_scan import DOWN, MalwareFound, ScannerDown
from app.voice.audio import scanned_seconds
from app.voice.runtime import VoiceRuntime

from ..upload_scanners import EICAR, EICAR_SIGNATURE, ScriptedScanner
from .fakes import SESSION_ID, MemoryStore, session
from .listen_fakes import MemoryObjects
from .test_voice_routes import Client

RECORDING = b"recorded"
INFECTED = RECORDING + EICAR.encode("ascii")
FOUND = f"The file was refused: the malware scan found {EICAR_SIGNATURE} in it."
TURNS = f"/api/voice/session/{SESSION_ID}/turns"
WEBM = "audio/webm"


class Measure:
    def __init__(self) -> None:
        self.heard: list[bytes] = []

    async def __call__(self, content: bytes) -> float:
        self.heard.append(content)
        return 3.0


def live_call() -> tuple[MemoryStore, Client]:
    now = datetime.now(UTC)
    store = MemoryStore()
    store.sessions[SESSION_ID] = session(started_at=now, expires_at=now + timedelta(seconds=60))
    return store, Client(store)


def artisan_upload(measure: Measure) -> TestClient:
    runtime = VoiceRuntime(client=httpx.AsyncClient(), objects=MemoryObjects(), measure=measure)
    app = FastAPI()

    @app.post("/upload")
    async def upload(request: Request) -> dict[str, int]:
        heard = await artisan_routes._upload(request, runtime)
        return {"seconds": heard.least_seconds}

    return TestClient(app)


async def test_a_recording_is_scanned_whole_before_it_is_measured(upload_scanner: ScriptedScanner) -> None:
    measure = Measure()
    assert await scanned_seconds(RECORDING, WEBM, measure) == 3
    assert upload_scanner.scanned == [RECORDING] and measure.heard == [RECORDING]


async def test_a_recording_carrying_the_eicar_test_file_is_refused_unmeasured() -> None:
    measure = Measure()
    with pytest.raises(MalwareFound, match=EICAR_SIGNATURE):
        await scanned_seconds(INFECTED, WEBM, measure)
    assert measure.heard == []


async def test_with_the_scanner_down_no_recording_is_measured(upload_scanner: ScriptedScanner) -> None:
    upload_scanner.down = True
    measure = Measure()
    with pytest.raises(ScannerDown, match="not answering"):
        await scanned_seconds(RECORDING, WEBM, measure)
    assert measure.heard == []


def test_a_call_turn_carrying_the_eicar_test_file_is_refused_by_name_and_takes_no_turn() -> None:
    store, client = live_call()
    response = client.http.post(TURNS, files={"audio": ("a.webm", INFECTED, WEBM)})
    assert response.status_code == 422 and response.json()["detail"] == FOUND
    assert store.sessions[SESSION_ID].turn_count == 0 and store.ledger == {}


def test_a_call_turn_sent_while_the_scanner_is_down_is_refused_and_takes_no_turn(
    upload_scanner: ScriptedScanner,
) -> None:
    upload_scanner.down = True
    store, client = live_call()
    response = client.http.post(TURNS, files={"audio": ("a.webm", RECORDING, WEBM)})
    assert response.status_code == 503 and response.json()["detail"] == DOWN
    assert store.sessions[SESSION_ID].turn_count == 0 and store.ledger == {}


def test_a_clean_call_turn_is_scanned_and_taken(upload_scanner: ScriptedScanner) -> None:
    _, client = live_call()
    response = client.http.post(TURNS, files={"audio": ("a.webm", RECORDING, WEBM)})
    assert response.status_code == 200 and "event: done" in response.text
    assert upload_scanner.scanned == [RECORDING]


def test_an_artisan_recording_carrying_the_eicar_test_file_is_refused_by_name() -> None:
    measure = Measure()
    response = artisan_upload(measure).post("/upload", files={"audio": ("a.webm", INFECTED, WEBM)})
    assert response.status_code == 422 and response.json()["detail"] == FOUND
    assert measure.heard == []


def test_an_artisan_recording_sent_while_the_scanner_is_down_is_refused_unmeasured(
    upload_scanner: ScriptedScanner,
) -> None:
    upload_scanner.down = True
    measure = Measure()
    response = artisan_upload(measure).post("/upload", files={"audio": ("a.webm", RECORDING, WEBM)})
    assert response.status_code == 503 and response.json()["detail"] == DOWN
    assert measure.heard == []


def test_a_clean_artisan_recording_is_scanned_then_measured(upload_scanner: ScriptedScanner) -> None:
    measure = Measure()
    response = artisan_upload(measure).post("/upload", files={"audio": ("a.webm", RECORDING, WEBM)})
    assert response.status_code == 200 and response.json() == {"seconds": 3}
    assert upload_scanner.scanned == [RECORDING] and measure.heard == [RECORDING]
