import importlib.util
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import (
    ArticleSection,
    Claim,
    Concept,
    Craft,
    CraftCategory,
    CuratedClaim,
    KnowledgePiece,
    KnowledgePieceSubject,
)

pytestmark = pytest.mark.db

MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0032_knowledge_fields.py"
CRAFT = uuid.UUID("5e7a0000-0000-4000-8000-000000000001")
CATEGORY = uuid.UUID("5e7a0000-0000-4000-8000-000000000002")
MATERIAL = uuid.UUID("5e7a0000-0000-4000-8000-000000000003")
OUTCOME = uuid.UUID("5e7a0000-0000-4000-8000-000000000004")
CURATED = uuid.UUID("5e7a0000-0000-4000-8000-0000000000a1")
PIECED = uuid.UUID("5e7a0000-0000-4000-8000-0000000000a2")
TYPED = uuid.UUID("5e7a0000-0000-4000-8000-0000000000a3")
UNTYPED = uuid.UUID("5e7a0000-0000-4000-8000-0000000000a4")
EARLY = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            opened = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            await _seed(opened)
            yield opened
            await opened.close()
        finally:
            await transaction.rollback()


async def _seed(session: AsyncSession) -> None:
    session.add(Craft(id=CRAFT, name="Field Test Craft", slug="Field-Test-Craft"))
    session.add(
        CraftCategory(id=CATEGORY, slug="field-test-category", name="Field Test Category", sortOrder=999)
    )
    await session.flush()
    session.add(Concept(id=MATERIAL, craftId=CRAFT, type="MATERIAL", name="Alum"))
    session.add(Concept(id=OUTCOME, craftId=CRAFT, type="OUTCOME", name="A bright red"))
    await session.flush()
    for claim_id, subject in ((CURATED, MATERIAL), (PIECED, MATERIAL), (TYPED, MATERIAL), (UNTYPED, OUTCOME)):
        session.add(_claim(claim_id, subject))
    await session.flush()


def _claim(claim_id: uuid.UUID, subject: uuid.UUID, **changes: Any) -> Claim:
    values: dict[str, Any] = {
        "id": claim_id,
        "subjectType": "CONCEPT",
        "subjectId": subject,
        "predicate": "states",
        "text": f"A stated fact {claim_id}.",
        "evidenceLevel": "PROVISIONAL",
        "origin": "IMPORT",
    }
    return Claim(**(values | changes))


def _piece(facet: str, claim_ids: list[uuid.UUID], created: datetime, **changes: Any) -> KnowledgePiece:
    values: dict[str, Any] = {
        "craftId": CRAFT,
        "kind": "prose",
        "facet": facet,
        "topicKey": f"test:{facet.lower()}",
        "language": "en",
        "depth": "BASIC",
        "payload": {},
        "claimIds": claim_ids,
        "sourceIds": ["S01"],
        "contentHash": "0" * 64,
        "createdAt": created,
    }
    return KnowledgePiece(**(values | changes))


def _migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("knowledge_fields_migration", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _refused(session: AsyncSession, row: object) -> bool:
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError:
        return True
    return False


async def _fields(session: AsyncSession, claim_id: uuid.UUID) -> tuple[str | None, list[str]]:
    row = (
        await session.execute(
            text('SELECT "field", "fields" FROM "Claim" WHERE "id" = :id'), {"id": claim_id}
        )
    ).one()
    return row[0], list(row[1])


async def test_the_backfill_takes_curated_then_first_piece_then_concept_type(session: AsyncSession) -> None:
    session.add(CuratedClaim(claimId=CURATED, craftId=CRAFT, key="C900", discipline="HISTORY"))
    session.add(_piece("CLIMATE", [PIECED], EARLY))
    session.add(_piece("ECOLOGY", [PIECED, CURATED], EARLY + timedelta(days=1)))
    session.add(_piece("CHEMISTRY", [CURATED], EARLY + timedelta(days=2)))
    await session.flush()
    for statement in _migration().backfill_statements():
        await session.execute(text(statement))
    assert await _fields(session, CURATED) == ("HISTORY", ["CHEMISTRY", "ECOLOGY"])
    assert await _fields(session, PIECED) == ("CLIMATE", ["ECOLOGY"])
    assert await _fields(session, TYPED) == ("MATERIALS", [])
    assert await _fields(session, UNTYPED) == (None, [])


async def test_a_claim_names_known_fields_its_primary_once_and_secondaries_only_beside_one(
    session: AsyncSession,
) -> None:
    def other(**changes: Any) -> Claim:
        return _claim(uuid.uuid4(), MATERIAL, **changes)

    assert await _refused(session, other(field="ASTROLOGY"))
    assert await _refused(session, other(field="HISTORY", fields=["HISTORY"]))
    assert await _refused(session, other(field=None, fields=["HISTORY"]))
    assert await _refused(session, other(field="HISTORY", fields=["NUMEROLOGY"]))
    assert not await _refused(session, other(field="SOCIETY", fields=["POLICY", "HISTORY"]))


def _section(version: int, status: str, **changes: Any) -> ArticleSection:
    values: dict[str, Any] = {
        "craftId": CRAFT,
        "field": "HISTORY",
        "version": version,
        "status": status,
        "sentences": [{"text": "Khatri families moved to Kachchh.", "claimIds": [str(CURATED)]}],
    }
    return ArticleSection(**(values | changes))


async def test_a_subject_field_has_one_published_section_and_versions_once(session: AsyncSession) -> None:
    assert not await _refused(session, _section(1, "PUBLISHED"))
    assert await _refused(session, _section(2, "PUBLISHED"))
    assert not await _refused(session, _section(2, "PROPOSED"))
    assert await _refused(session, _section(2, "PROPOSED"))
    assert not await _refused(session, _section(1, "PUBLISHED", field="POLICY"))


async def test_a_section_belongs_to_exactly_one_subject_and_holds_sentences(session: AsyncSession) -> None:
    assert await _refused(session, _section(1, "PROPOSED", categoryId=CATEGORY))
    assert await _refused(session, _section(1, "PROPOSED", craftId=None))
    assert await _refused(session, _section(1, "PROPOSED", sentences=[]))
    assert await _refused(session, _section(1, "UNKNOWN"))
    assert not await _refused(session, _section(1, "PUBLISHED", craftId=None, categoryId=CATEGORY))


async def test_a_registered_component_has_a_unique_label_a_title_and_a_description(
    session: AsyncSession,
) -> None:
    label = "field-test-craft/chemistry/alum-mordant-player"
    titled = {"title": "Alum mordant", "description": "Shows alum binding dye to cotton, step by step."}
    assert await _refused(session, _piece("CHEMISTRY", [TYPED], EARLY, label=label))
    assert await _refused(session, _piece("CHEMISTRY", [TYPED], EARLY, label="Not A Label", **titled))
    assert not await _refused(session, _piece("CHEMISTRY", [TYPED], EARLY, label=label, **titled))
    assert await _refused(session, _piece("PROCESS", [TYPED], EARLY, label=label, **titled))
    assert await _refused(session, _piece("CHEMISTRY", [TYPED], EARLY, fields=["CHEMISTRY"]))
    assert not await _refused(session, _piece("CHEMISTRY", [TYPED], EARLY, fields=["MATERIALS"]))


async def test_a_component_subject_names_exactly_the_kind_it_says(session: AsyncSession) -> None:
    piece = _piece("CHEMISTRY", [TYPED], EARLY)
    session.add(piece)
    await session.flush()

    def subject(kind: str, **columns: Any) -> KnowledgePieceSubject:
        return KnowledgePieceSubject(pieceId=piece.id, kind=kind, **columns)

    assert await _refused(session, subject("CRAFT", conceptId=MATERIAL))
    assert await _refused(session, subject("CRAFT", craftId=CRAFT, conceptId=MATERIAL))
    assert await _refused(session, subject("PLACE", placeKey="kachchh"))
    assert not await _refused(session, subject("PLACE", placeKey="lgd:449"))
    assert not await _refused(session, subject("CRAFT", craftId=CRAFT))
    assert await _refused(session, subject("CRAFT", craftId=CRAFT))
    assert not await _refused(session, subject("CONCEPT", conceptId=MATERIAL))
