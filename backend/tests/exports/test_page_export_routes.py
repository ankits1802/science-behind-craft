import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, replace
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.api import document_reads, export_deps
from app.api.routes import craft_monograph, page_documents
from app.core.db import get_session
from app.core.errors import ExternalFailure
from app.core.rate_limit import EXPORT_BUILDS_PER_WINDOW
from app.main import create_app
from app.research.document_parts import compact_json
from app.research.monograph_document import MonographDocument
from app.services import export_files, knowledge_view, page_export_files
from app.services.export_files import lesson_file_link
from app.services.export_store import BUSY_RETRY_SECONDS, WaitedSlots
from app.services.monograph_document import document_body, document_hash
from app.services.page_export_files import PAGE_EXPORT_BUILDS_AT_ONCE
from app.services.page_translation_serving import ServedPage, ShownPage
from app.services.stored_documents import GeneratedRead, StoredCopy

from ..learning.lesson_fixtures import FakeBucket, golden_pack

FAMILY, CATEGORY, CRAFT = "Other-Textiles", "Textile-Craft-Category", "Bagh-Print"
VISITOR, NEIGHBOUR = "203.0.113.5", "203.0.113.6"
LESSON_OWNER = uuid.UUID(int=7)
BUILT = b"PK\x03\x04 a page export"


class QuietSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class NoPictures:
    async def picture(self, url: str) -> bytes:
        raise ExternalFailure(f"{url} is not read in this test")


@dataclass
class Held:
    bucket: FakeBucket = field(default_factory=FakeBucket)
    stale: bool = False
    queued: list[tuple[str, str]] = field(default_factory=list)
    built: list[str] = field(default_factory=list)
    app: Any = field(default_factory=create_app)

    def read(self, kind: str, slug: str) -> GeneratedRead:
        copy = stored(page(kind, slug), current=not self.stale)
        return GeneratedRead(SimpleNamespace(kind=kind, slug=slug), copy, rebuild=self.stale)  # type: ignore[arg-type]

    async def get(self, path: str, *, address: str = VISITOR) -> httpx.Response:
        self.app.dependency_overrides[get_session] = quiet_session
        transport = httpx.ASGITransport(app=self.app, client=(address, 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)


def page(kind: str, slug: str) -> MonographDocument:
    content = {
        "craftSlug": slug,
        "sources": {},
        "citations": {},
        "citationClaims": {},
        "data": {},
        "units": {},
        "components": [],
        "layout": [],
    }
    return MonographDocument.model_validate(
        {
            "subjectKind": kind,
            "subjectSlug": slug,
            "title": slug.replace("-", " "),
            "version": 2,
            "content": content,
            "pageUrl": f"https://kalavigyan.example/crafts/{slug}",
        }
    )


def stored(document: MonographDocument, *, current: bool) -> StoredCopy:
    text = compact_json(document_body(document))
    return StoredCopy(text, document.version, document_hash(document), document.language, current)


async def quiet_session() -> AsyncIterator[QuietSession]:
    yield QuietSession()


@pytest.fixture
def held(monkeypatch: pytest.MonkeyPatch) -> Held:
    state = Held()

    async def generated_read(session: Any, kind: str, slug: str) -> GeneratedRead:
        return state.read(kind, slug)

    async def resolve_craft(session: Any, slug: str) -> Any:
        return SimpleNamespace(slug=slug, isCatchAll=False, stateOfPractice=["Madhya Pradesh"])

    async def document_row(session: Any, kind: str, slug: str, *, language: str, version: Any) -> None:
        return None

    async def generated_fallback(session: Any, craft: Any) -> GeneratedRead:
        return state.read("craft", craft.slug)

    async def in_english(
        session: Any, page_key: Any, english: ServedPage, *, tag: str, language: str
    ) -> ShownPage:
        return ShownPage(english, wrote=False)

    async def rebuild_wanted(kind: str, slug: str) -> None:
        state.queued.append((kind, slug))

    def page_file(document: MonographDocument, fmt: str, pictures: Any = None) -> bytes:
        state.built.append(f"{document.subject_slug}.{fmt}")
        return BUILT

    monkeypatch.setattr(page_documents, "generated_read", generated_read)
    monkeypatch.setattr(knowledge_view, "resolve_craft", resolve_craft)
    monkeypatch.setattr(craft_monograph, "document_row", document_row)
    monkeypatch.setattr(craft_monograph, "generated_fallback", generated_fallback)
    monkeypatch.setattr(document_reads, "page_in_language", in_english)
    monkeypatch.setattr(document_reads, "rebuild_wanted", rebuild_wanted)
    monkeypatch.setattr(page_export_files, "page_file", page_file)
    monkeypatch.setattr(export_files, "picture_files", lambda client, *, site=None: NoPictures())
    monkeypatch.setattr(export_deps, "media_bucket", lambda: state.bucket)
    free = WaitedSlots(PAGE_EXPORT_BUILDS_AT_ONCE, wait_seconds=0.05, retry_after=BUSY_RETRY_SECONDS)
    monkeypatch.setattr(export_deps, "_page_export_builds", free)
    return state


@pytest.mark.parametrize(
    ("path", "subject"),
    [
        (f"/api/families/{FAMILY}/monograph/pdf", ("family", FAMILY)),
        (f"/api/categories/{CATEGORY}/monograph/docx", ("category", CATEGORY)),
        (f"/api/crafts/{CRAFT}/monograph/pdf", ("craft", CRAFT)),
    ],
)
async def test_an_export_of_a_stale_page_queues_its_rebuild_and_of_a_current_page_none(
    path: str, subject: tuple[str, str], held: Held
) -> None:
    current = await held.get(path)
    assert current.status_code == 200, current.text
    assert current.headers["cache-control"] == "private, no-cache"
    assert held.queued == []
    held.stale = True
    stale = await held.get(path)
    assert stale.status_code == 200, stale.text
    assert held.queued == [subject] and len(held.built) == 1


async def test_a_page_export_with_no_free_slot_is_refused_with_a_retry_and_an_answer_export_still_runs(
    held: Held, monkeypatch: pytest.MonkeyPatch
) -> None:
    full = WaitedSlots(0, wait_seconds=0.05, retry_after=BUSY_RETRY_SECONDS)
    monkeypatch.setattr(export_deps, "_page_export_builds", full)
    held.stale = True
    refused = await held.get(f"/api/families/{FAMILY}/monograph/pdf")
    assert refused.status_code == 503, refused.text
    assert refused.headers["retry-after"] == "30"
    assert held.built == [] and held.bucket.stored == {}
    assert held.queued == [("family", FAMILY)]
    async with asynccontextmanager(export_deps.export_tools)() as tools:
        link = await lesson_file_link(tools, LESSON_OWNER, golden_pack(), {}, "html")
    assert link.format == "html" and len(held.bucket.stored) == 1


async def test_a_caller_over_the_build_allowance_is_refused_but_still_gets_a_filed_file(held: Held) -> None:
    paths = [f"/api/families/Family-{n}/monograph/pdf" for n in range(EXPORT_BUILDS_PER_WINDOW + 1)]
    answers = [(await held.get(path)).status_code for path in paths]
    assert answers == [200] * EXPORT_BUILDS_PER_WINDOW + [429]
    assert len(held.built) == EXPORT_BUILDS_PER_WINDOW
    spent = await held.get(paths[-1])
    assert spent.status_code == 429 and int(spent.headers["retry-after"]) >= 1
    assert (await held.get(paths[0])).status_code == 200
    assert (await held.get(paths[-1], address=NEIGHBOUR)).status_code == 200
    assert len(held.built) == EXPORT_BUILDS_PER_WINDOW + 1


async def test_a_craft_export_never_files_a_version_a_removal_reached_but_files_one_still_kept(
    held: Held, monkeypatch: pytest.MonkeyPatch
) -> None:
    earlier = stored(page("craft", CRAFT).model_copy(update={"version": 1}), current=False)
    kept = {1: replace(earlier, withheld=True)}

    async def superseded(session: Any, subject: Any, version: int) -> StoredCopy | None:
        return kept.get(version)

    monkeypatch.setattr(document_reads, "superseded_fallback", superseded)
    path = f"/api/crafts/{CRAFT}/monograph/pdf?version=1"
    refused = await held.get(path)
    assert refused.status_code == 404, refused.text
    assert refused.json()["detail"] == craft_monograph.NO_VERSION_DETAIL
    assert held.built == [] and held.bucket.stored == {}
    named = await held.get(f"/api/crafts/{CRAFT}/monograph?version=1")
    assert named.status_code == 200 and named.json()["version"] == 1
    kept[1] = earlier
    filed = await held.get(path)
    assert filed.status_code == 200, filed.text
    assert held.built == [f"{CRAFT}.pdf"]
