import uuid
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from typing import Any

import httpx
import pytest
from starlette.requests import HTTPConnection

from app.api import export_deps
from app.api.routes import shared
from app.core.db import get_session
from app.core.errors import ExternalFailure
from app.core.rate_limit import EXPORT_BUILDS_PER_WINDOW, export_build_attempt
from app.main import create_app
from app.research.explainer_versions import ExplainerVersionDocument
from app.research.lessons import LessonPack
from app.services import export_files
from app.services.export_files import lesson_file_link
from app.services.export_store import BUILDS_BUSY, BUSY_RETRY_SECONDS, WaitedSlots
from app.services.shared_files import SHARED_EXPORT_BUILDS_AT_ONCE, SHARED_PREFIX

from .lesson_fixtures import FakeBucket, first_version, golden_pack, picture_bytes

NOW = datetime(2026, 11, 25, 10, 20, tzinfo=UTC)
VISITOR, NEIGHBOUR = "203.0.113.5", "203.0.113.6"
OWNER = uuid.UUID(int=31)
TOKEN = "k7Qm2vX9pL4sT8wB1nR6yC3dF5gH0jZa"
SPENT_DETAIL = export_deps.BUILDS_SPENT_DETAIL
LESSON_FILE = f"/api/shared/lessons/{TOKEN}/files/html"
ANSWER_FILE = f"/api/shared/answers/{TOKEN}/pdf"


def token(n: int) -> str:
    return f"{'s' * 30}{n:02d}"


class QuietSession:
    async def commit(self) -> None:
        return None


async def quiet_session() -> AsyncIterator[QuietSession]:
    yield QuietSession()


@dataclass
class Pictures:
    readable: bool = True
    asked: int = 0

    async def picture(self, url: str) -> bytes:
        self.asked += 1
        if not self.readable:
            raise ExternalFailure(f"{url} is not read in this test")
        return picture_bytes()


@dataclass
class Held:
    bucket: FakeBucket = field(default_factory=FakeBucket)
    pictures: Pictures = field(default_factory=Pictures)
    packs: dict[str, LessonPack] = field(default_factory=dict)
    built: list[str] = field(default_factory=list)
    recorded: list[tuple[str, list[str]]] = field(default_factory=list)
    app: Any = field(default_factory=create_app)

    async def get(self, path: str, *, address: str = VISITOR) -> httpx.Response:
        self.app.dependency_overrides[get_session] = quiet_session
        transport = httpx.ASGITransport(app=self.app, client=(address, 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    def shared_files(self) -> list[str]:
        return sorted(key for key in self.bucket.stored if key.startswith(SHARED_PREFIX))


def shared_packs() -> dict[str, LessonPack]:
    parts = {
        token(n): golden_pack().model_copy(update={"title": f"Mordants, part {n}"})
        for n in range(EXPORT_BUILDS_PER_WINDOW + 1)
    }
    return {TOKEN: golden_pack(), **parts}


def slots(free: int) -> WaitedSlots:
    return WaitedSlots(free, wait_seconds=0.05, retry_after=BUSY_RETRY_SECONDS)


@pytest.fixture
def held(monkeypatch: pytest.MonkeyPatch) -> Held:
    state = Held(packs=shared_packs())
    opened = export_files.opened_export_tools

    @asynccontextmanager
    async def at_now(*arguments: Any, **options: Any) -> AsyncIterator[export_files.ExportTools]:
        async with opened(*arguments, **options) as tools:
            yield replace(tools, clock=lambda: NOW)

    async def shared_lesson(session: Any, asked: str) -> LessonPack | None:
        return state.packs.get(asked)

    async def shared_answer(session: Any, asked: str) -> ExplainerVersionDocument | None:
        return first_version() if asked == TOKEN else None

    async def record(session: Any, asked: str, keys: list[str], *, objects: Any) -> None:
        state.recorded.append((asked, list(keys)))

    async def no_dates(session: Any, cited: Any) -> dict[str, date]:
        return {}

    def deck(pack: LessonPack, refs: Any, pictures: Mapping[uuid.UUID, Any]) -> bytes:
        state.built.append(pack.title)
        return b"<html>a lesson deck</html>"

    monkeypatch.setattr(shared, "shared_lesson", shared_lesson)
    monkeypatch.setattr(shared, "shared_answer", shared_answer)
    monkeypatch.setattr(shared, "record_shared_files", record)
    monkeypatch.setattr(export_deps, "accessed_dates", no_dates)
    monkeypatch.setattr(export_deps, "media_bucket", lambda: state.bucket)
    monkeypatch.setattr(export_deps, "opened_export_tools", at_now)
    monkeypatch.setattr(export_deps, "_shared_export_builds", slots(SHARED_EXPORT_BUILDS_AT_ONCE))
    monkeypatch.setattr(export_files, "picture_files", lambda client, *, site=None: state.pictures)
    monkeypatch.setattr(export_files, "LESSON_RENDERERS", {"html": deck})
    return state


async def owner_s_lesson_file() -> None:
    async with asynccontextmanager(export_deps.export_tools)() as tools:
        link = await lesson_file_link(tools, OWNER, golden_pack(), {}, "html")
    assert link.format == "html"


@pytest.mark.parametrize("path", [LESSON_FILE, ANSWER_FILE])
async def test_a_shared_file_with_no_free_slot_is_refused_with_a_retry_while_an_owner_s_file_builds(
    path: str, held: Held, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(export_deps, "_shared_export_builds", slots(0))
    refused = await held.get(path)
    assert refused.status_code == 503, refused.text
    assert refused.headers["retry-after"] == "30"
    assert refused.json() == {"detail": BUILDS_BUSY}
    assert held.bucket.stored == {} and held.recorded == []
    await owner_s_lesson_file()
    assert held.built == [golden_pack().title] and len(held.bucket.stored) == 1
    assert held.shared_files() == []


async def test_a_filed_shared_file_is_given_whatever_its_slots_hold(
    held: Held, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = await held.get(LESSON_FILE)
    assert first.status_code == 200, first.text
    assert first.headers["cache-control"] == "private, no-cache"
    monkeypatch.setattr(export_deps, "_shared_export_builds", slots(0))
    again = await held.get(LESSON_FILE)
    assert again.status_code == 200, again.text
    assert again.json()["fileName"] == first.json()["fileName"]
    assert len(held.built) == 1 and len(held.shared_files()) == 1
    assert held.recorded == [(TOKEN, held.shared_files()), (TOKEN, held.shared_files())]


async def test_a_caller_over_the_build_allowance_is_refused_a_new_shared_file_but_given_a_filed_one(
    held: Held,
) -> None:
    paths = [f"/api/shared/lessons/{token(n)}/files/html" for n in range(EXPORT_BUILDS_PER_WINDOW + 1)]
    answers = [(await held.get(path)).status_code for path in paths]
    assert answers == [200] * EXPORT_BUILDS_PER_WINDOW + [429]
    spent = await held.get(paths[-1])
    assert spent.status_code == 429 and int(spent.headers["retry-after"]) >= 1
    assert spent.json() == {"detail": SPENT_DETAIL}
    assert len(held.built) == EXPORT_BUILDS_PER_WINDOW
    assert (await held.get(paths[0])).status_code == 200
    assert (await held.get(paths[-1], address=NEIGHBOUR)).status_code == 200
    assert len(held.built) == EXPORT_BUILDS_PER_WINDOW + 1


async def test_a_caller_who_spent_the_allowance_on_page_files_is_refused_a_new_shared_file(
    held: Held,
) -> None:
    visitor = HTTPConnection({"type": "http", "client": (VISITOR, 50000), "headers": []})
    for _ in range(EXPORT_BUILDS_PER_WINDOW):
        assert (await export_build_attempt(visitor, None))[0]
    assert (await held.get(LESSON_FILE)).status_code == 429
    assert (await held.get(LESSON_FILE, address=NEIGHBOUR)).status_code == 200
    assert len(held.built) == 1


async def test_a_shared_file_built_while_a_picture_was_unread_serves_its_hour_and_an_owner_s_never(
    held: Held,
) -> None:
    held.pictures.readable = False
    first = await held.get(LESSON_FILE)
    again = await held.get(LESSON_FILE, address=NEIGHBOUR)
    assert first.status_code == again.status_code == 200, first.text
    assert len(held.built) == 1 and held.pictures.asked >= 1
    assert len(held.shared_files()) == 1
    await owner_s_lesson_file()
    await owner_s_lesson_file()
    assert len(held.built) == 3
