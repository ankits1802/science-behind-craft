import hashlib
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.routes import molecules
from app.core.db import get_session
from app.core.errors import ExternalFailure
from app.main import create_app
from app.models import User

from ..readers import sign_in_as
from ..sources.recorded import recorded
from ..voice.listen_fakes import MemoryObjects

PATH = "/api/molecules/6293/conformer"
ALIZARIN_SDF = recorded("pubchem_conformer.sdf").decode("ascii").strip()
READER = User(id=uuid.UUID(int=7), name="Meera Rao", email="meera@example.org", role="STUDENT")
COMPOUND = uuid.UUID(int=6293)


@dataclass
class Calls:
    made: list[str] = field(default_factory=list)

    def held_while(self, outside: str) -> list[int]:
        held = False
        found: list[int] = []
        for index, call in enumerate(self.made):
            if call == "query":
                held = True
            elif call == "commit":
                held = False
            elif call.startswith(outside) and held:
                found.append(index)
        return found


@dataclass
class RecordingSession:
    calls: Calls
    stored: bool = True

    async def execute(self, statement: Any) -> None:
        self.calls.made.append("query")

    async def scalar(self, statement: Any) -> uuid.UUID | None:
        self.calls.made.append("query")
        return COMPOUND if self.stored else None

    async def commit(self) -> None:
        self.calls.made.append("commit")


@dataclass
class CountingSource:
    calls: Calls
    sdf: str | None = ALIZARIN_SDF
    failure: Exception | None = None
    asked: list[int] = field(default_factory=list)

    async def conformer(self, cid: int) -> str | None:
        self.calls.made.append("external: pubchem")
        self.asked.append(cid)
        if self.failure is not None:
            raise self.failure
        return self.sdf


@dataclass
class RecordingBucket:
    calls: Calls
    kept: MemoryObjects = field(default_factory=MemoryObjects)

    async def get(self, key: str) -> bytes | None:
        self.calls.made.append("external: bucket get")
        return await self.kept.get(key)

    async def put(self, key: str, body: bytes, *, content_type: str) -> None:
        self.calls.made.append("external: bucket put")
        await self.kept.put(key, body, content_type=content_type)


@dataclass
class Route:
    http: TestClient
    calls: Calls
    source: CountingSource


def route(
    monkeypatch: pytest.MonkeyPatch,
    *,
    stored: bool = True,
    signed_in: bool = True,
    bucket: bool = True,
    **source: Any,
) -> Route:
    calls = Calls()
    counting = CountingSource(calls, **source)
    kept = RecordingBucket(calls)

    async def recording_session() -> AsyncIterator[RecordingSession]:
        yield RecordingSession(calls, stored=stored)

    async def reader(session: RecordingSession = Depends(get_session)) -> User:
        await session.execute("the signed-in user")
        return READER

    async def pubchem(live: Any, sessions: Any) -> CountingSource:
        calls.made.append("external: pubchem adapter")
        return counting

    monkeypatch.setattr(molecules, "media_bucket", lambda: kept if bucket else None)
    monkeypatch.setattr(molecules, "live_pubchem", pubchem)
    monkeypatch.setattr(molecules, "sessionmaker", lambda: None)
    app = create_app()
    app.dependency_overrides[get_session] = recording_session
    if signed_in:
        sign_in_as(app, reader)
    return Route(TestClient(app), calls, counting)


def test_a_signed_in_reader_gets_the_stored_compound_s_3d_sdf(monkeypatch: pytest.MonkeyPatch) -> None:
    found = route(monkeypatch)
    first, second = found.http.get(PATH), found.http.get(PATH)
    assert first.status_code == second.status_code == 200
    assert first.headers["content-type"].startswith("chemical/x-mdl-sdfile")
    assert first.headers["cache-control"] == "private, no-cache"
    assert first.headers["etag"] == f'"{hashlib.sha256(ALIZARIN_SDF.encode("utf-8")).hexdigest()}"'
    assert first.text == second.text == ALIZARIN_SDF
    assert found.source.asked == [6293]


def test_no_bucket_or_pubchem_call_starts_while_a_connection_is_held(monkeypatch: pytest.MonkeyPatch) -> None:
    found = route(monkeypatch)
    assert found.http.get(PATH).status_code == 200
    assert found.calls.made == [
        "query",
        "query",
        "commit",
        "external: pubchem adapter",
        "external: bucket get",
        "external: pubchem",
        "external: bucket put",
    ]
    assert found.calls.held_while("external") == []


@pytest.mark.parametrize(
    ("changes", "status", "asked"),
    [
        ({"stored": False}, 404, []),
        ({"sdf": None}, 404, [6293]),
        ({"failure": ExternalFailure("pubchem answered 503", kind="unavailable")}, 503, [6293]),
        ({"bucket": False}, 503, []),
    ],
    ids=["not a stored compound", "no 3D conformer", "PubChem down", "no media bucket"],
)
def test_nothing_to_draw_is_404_and_a_failure_503(
    monkeypatch: pytest.MonkeyPatch, changes: dict[str, Any], status: int, asked: list[int]
) -> None:
    found = route(monkeypatch, **changes)
    response = found.http.get(PATH)
    assert response.status_code == status
    assert found.source.asked == asked
    assert found.calls.held_while("external") == []
    if status == 503:
        assert response.json()["detail"] == molecules.UNAVAILABLE_DETAIL


def test_an_anonymous_reader_gets_the_structure_and_a_cid_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anonymous = route(monkeypatch, signed_in=False).http.get(PATH)
    assert (anonymous.status_code, anonymous.text) == (200, ALIZARIN_SDF)
    assert anonymous.headers["cache-control"] == "public, max-age=300"
    found = route(monkeypatch)
    assert found.http.get("/api/molecules/0/conformer").status_code == 422
    assert found.source.asked == []
