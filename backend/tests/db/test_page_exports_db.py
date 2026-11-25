import asyncio
import zipfile
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from xml.etree import ElementTree

import httpx
import pytest
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.export_deps import page_export_tools
from app.core.db import get_session
from app.main import app
from app.services.apa_references import apa_references
from app.services.export_files import ExportTools

from ..learning.lesson_fixtures import FakeBucket, picture_bytes
from .page_documents_seed import CATEGORY_SLUG, CRAFT_SLUG, FAMILY_SLUG, seed
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 25, 6, 30, tzinfo=UTC)
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CRAFT_PICTURE = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Page_docs.jpg/1280px-Page_docs.jpg"


class Pictures:
    def __init__(self) -> None:
        self.asked: list[str] = []

    async def picture(self, url: str) -> bytes:
        self.asked.append(url)
        return picture_bytes("PNG", (1280, 960))


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await seed(opened)
        yield opened


async def exported(session: AsyncSession, path: str, held: tuple[FakeBucket, Pictures]) -> httpx.Response:
    bucket, pictures = held

    async def this_session() -> AsyncIterator[Any]:
        yield session

    async def these_tools() -> AsyncIterator[ExportTools]:
        yield ExportTools(
            objects=bucket,
            pictures=pictures,
            apa=apa_references,
            clock=lambda: NOW,
            builds=asyncio.Semaphore(1),
        )

    app.dependency_overrides[get_session] = this_session
    app.dependency_overrides[page_export_tools] = these_tools
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)
    finally:
        for dependency in (get_session, page_export_tools):
            app.dependency_overrides.pop(dependency, None)


def stored(bucket: FakeBucket) -> bytes:
    [(body, _)] = bucket.stored.values()
    return body


def pdf_text(data: bytes) -> str:
    return " ".join(" ".join(page.extract_text() for page in PdfReader(BytesIO(data)).pages).split())


def word_paragraphs(data: bytes) -> list[str]:
    with zipfile.ZipFile(BytesIO(data)) as package:
        root = ElementTree.fromstring(package.read("word/document.xml"))
    return ["".join(node.text or "" for node in p.iter(f"{WORD}t")) for p in root.iter(f"{WORD}p")]


async def test_a_family_page_exports_its_overview_and_sources_as_a_family_page_pdf(
    session: AsyncSession,
) -> None:
    bucket = FakeBucket()
    answer = await exported(session, f"/api/families/{FAMILY_SLUG}/monograph/pdf", (bucket, Pictures()))
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["format"] == "pdf"
    assert body["fileName"].startswith("KalaVigyan_Family-Page_2026-11-25_") and body["fileName"].endswith(
        ".pdf"
    )
    assert answer.headers["cache-control"] == "private, no-cache"
    text = pdf_text(stored(bucket))
    assert "Printers across India print with carved wooden blocks." in text and "Sources" in text


async def test_a_category_page_exports_its_overview_and_components_as_a_word_document(
    session: AsyncSession,
) -> None:
    bucket = FakeBucket()
    answer = await exported(session, f"/api/categories/{CATEGORY_SLUG}/monograph/docx", (bucket, Pictures()))
    assert answer.status_code == 200, answer.text
    assert answer.json()["fileName"].startswith("KalaVigyan_Category-Page_2026-11-25_")
    paragraphs = word_paragraphs(stored(bucket))
    assert paragraphs[0] == "Page Docs Test Category"
    assert any("Textile crafts dye, print and weave cloth." in paragraph for paragraph in paragraphs)
    assert "Sources" in paragraphs


async def test_a_craft_page_embeds_its_open_picture_read_at_the_paper_width(session: AsyncSession) -> None:
    bucket, pictures = FakeBucket(), Pictures()
    answer = await exported(session, f"/api/crafts/{CRAFT_SLUG}/monograph/docx", (bucket, pictures))
    assert answer.status_code == 200, answer.text
    assert pictures.asked == [CRAFT_PICTURE]
    with zipfile.ZipFile(BytesIO(stored(bucket))) as package:
        assert "word/media/figure1.jpeg" in package.namelist()
    paragraphs = word_paragraphs(stored(bucket))
    caption = paragraphs.index("A printed cloth held up")
    assert paragraphs.index("Photo: A. Printer, CC BY-SA 4.0, via Wikimedia Commons") > caption


async def test_an_unknown_family_or_category_is_404_and_another_format_is_422(session: AsyncSession) -> None:
    held = (FakeBucket(), Pictures())
    assert (await exported(session, "/api/families/No-Such-Family/monograph/pdf", held)).status_code == 404
    assert (
        await exported(session, "/api/categories/No-Such-Category/monograph/pdf", held)
    ).status_code == 404
    assert (await exported(session, f"/api/families/{FAMILY_SLUG}/monograph/txt", held)).status_code == 422
