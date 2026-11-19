import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Craft, MonographDocument as DocumentRow
from app.research.monograph_document import MonographDocument, fragment_file_name
from app.research.monograph_page import MonographContent
from app.services import monograph_document as authored
from app.services.monograph_document import store_document, stored_document
from app.services.monograph_load import load_monograph

from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 19, 12, tzinfo=UTC)
SLUG = "Monograph-Document-Test-Craft"
NAME = "Monograph Document Test Craft"
PLATE = "monograph-document-test-craft/design/plate"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        opened.add(Craft(id=uuid.UUID("40d0c000-0000-4000-8000-000000000001"), name=NAME, slug=SLUG))
        await opened.flush()
        yield opened


def _content() -> MonographContent:
    return MonographContent.model_validate(
        {
            "craftSlug": SLUG,
            "sources": {},
            "citations": {},
            "citationClaims": {},
            "data": {},
            "units": {
                "u1": {"chapter": "c", "tag": "p", "field": "DESIGN", "nodes": ["Alum"], "claimIds": []}
            },
            "components": [
                {
                    "label": PLATE,
                    "chapter": "c",
                    "anchor": "#plate",
                    "kind": "picture_plate",
                    "title": "Plate",
                    "description": "A plate.",
                    "field": "DESIGN",
                    "fields": [],
                    "subjects": [],
                }
            ],
            "layout": [
                {"chapter": "c", "kind": "component", "ref": PLATE, "within": None},
                {"chapter": "c", "kind": "unit", "ref": "u1", "within": PLATE},
            ],
        }
    )


def _document(title: str = NAME) -> MonographDocument:
    return MonographDocument(
        subject_kind="craft",
        subject_slug=SLUG,
        title=title,
        version=1,
        content=_content(),
        fragments={PLATE: '<figure id="plate">Alum</figure>'},
        page_url=f"https://kalavigyan.example/crafts/{SLUG}",
    )


async def _versions(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(DocumentRow.version).where(DocumentRow.subjectSlug == SLUG).order_by(DocumentRow.version)
    )
    return list(rows)


async def test_a_changed_document_is_stored_as_a_new_version_and_an_unchanged_one_is_not(
    session: AsyncSession,
) -> None:
    first = await store_document(session, _document())
    same = await store_document(session, _document().model_copy(update={"version": 4}))
    changed = await store_document(session, _document("Monograph Document Test Craft, revised"))
    assert (first, same, changed) == (1, None, 2)
    assert await _versions(session) == [1, 2]
    latest = await stored_document(session, "craft", SLUG)
    assert latest is not None
    assert (latest.version, latest.title) == (2, "Monograph Document Test Craft, revised")
    assert await stored_document(session, "category", SLUG) is None


async def test_loading_an_authored_monograph_stores_its_document_once(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(authored, "MONOGRAPHS_DIR", tmp_path)
    (tmp_path / SLUG / "fragments").mkdir(parents=True)
    (tmp_path / SLUG / "content.json").write_bytes(_content().model_dump_json(by_alias=True).encode("utf-8"))
    fragment = tmp_path / SLUG / "fragments" / fragment_file_name(PLATE)
    fragment.write_bytes(b'<figure id="plate"><kv-slot unit="u1"></kv-slot></figure>')
    first = await load_monograph(session, _content(), now=NOW)
    again = await load_monograph(session, _content(), now=NOW)
    assert (first.document_version, again.document_version) == (1, None)
    assert again.as_dict()["documentVersion"] is None
    stored = await stored_document(session, "craft", SLUG)
    assert stored is not None
    assert (stored.version, stored.title) == (1, NAME)
    assert stored.fragments == {PLATE: '<figure id="plate">Alum</figure>'}
    assert stored.page_url.endswith(f"/crafts/{SLUG}")


async def test_a_craft_without_authored_files_stores_no_document(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(authored, "MONOGRAPHS_DIR", tmp_path)
    loaded = await load_monograph(session, _content(), now=NOW)
    assert loaded.document_version is None
    assert await _versions(session) == []
