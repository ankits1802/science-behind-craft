import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.core.errors import InvalidInput
from app.models import (
    Compound,
    Concept,
    Craft,
    KnowledgePiece,
    KnowledgePieceSubject,
    Material,
    Process,
    ProcessStage,
    StageMaterial,
)
from app.research.knowledge_api import ComponentSubject
from app.services.component_library import library_components

pytestmark = pytest.mark.db

SLUG = "Component-Library-Test-Craft"
CRAFT = uuid.UUID("c0b10000-0000-4000-8000-000000000001")
OTHER_CRAFT = uuid.UUID("c0b10000-0000-4000-8000-000000000002")
ALUM = uuid.UUID("c0b10000-0000-4000-8000-000000000003")
INDIGO_REDUCTION = uuid.UUID("c0b10000-0000-4000-8000-000000000004")
LACQUER = uuid.UUID("c0b10000-0000-4000-8000-000000000005")
SECRET_RECIPE = uuid.UUID("c0b10000-0000-4000-8000-000000000006")
TANNIC_ACID = uuid.UUID("c0b10000-0000-4000-8000-000000000007")
PROCESS = uuid.UUID("c0b10000-0000-4000-8000-000000000008")
VAT = uuid.UUID("c0b10000-0000-4000-8000-000000000009")
MYROBALAN = uuid.UUID("c0b10000-0000-4000-8000-00000000000a")
CLAIM = uuid.UUID("c0b10000-0000-4000-8000-00000000000b")
HIDDEN_AT = datetime(2026, 11, 19, tzinfo=UTC)

OWN = "component-library-test-craft/chemistry/alum-mordant"
SECRET = "component-library-test-craft/chemistry/secret-recipe"
INDIGO_PLAYER = "shared/chemistry/indigo-reduction-player"
TANNIN_MOLECULE = "shared/chemistry/tannic-acid-molecule"
ALUM_CRYSTAL = "shared/materials/alum-crystal"
CRAFT_LINKED = "shared/history/printers-route-map"
LACQUER_CURING = "shared/chemistry/lacquer-curing"
OTHER_TIMELINE = "component-library-other-craft/history/timeline"


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
    session.add(Craft(id=CRAFT, name="Component Library Test Craft", slug=SLUG))
    session.add(
        Craft(id=OTHER_CRAFT, name="Component Library Other Craft", slug="Component-Library-Other-Craft")
    )
    session.add(Concept(id=ALUM, craftId=CRAFT, type="MATERIAL", name="Alum"))
    session.add(Concept(id=INDIGO_REDUCTION, type="PROCESS_STAGE", name="Indigo reduction"))
    session.add(Concept(id=LACQUER, type="PROCESS_STAGE", name="Lacquer curing"))
    session.add(
        Concept(
            id=SECRET_RECIPE, craftId=CRAFT, type="MATERIAL", name="House recipe", sensitivity="RESTRICTED"
        )
    )
    session.add(Compound(id=TANNIC_ACID, name="Tannic acid"))
    session.add(Process(id=PROCESS, craftId=CRAFT, name="Dyeing"))
    await session.flush()
    session.add(
        ProcessStage(id=VAT, processId=PROCESS, ordinal=1, name="Indigo vat", conceptId=INDIGO_REDUCTION)
    )
    session.add(Material(id=MYROBALAN, name="Myrobalan", nameNorm="myrobalan", compoundId=TANNIC_ACID))
    await session.flush()
    session.add(StageMaterial(stageId=VAT, materialId=MYROBALAN))
    await session.flush()


def _component(label: str, title: str, description: str, **changes: Any) -> KnowledgePiece:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "kind": "prose",
        "facet": "CHEMISTRY",
        "topicKey": f"component:{label}",
        "language": "en",
        "depth": "EXPERT",
        "payload": {},
        "claimIds": [CLAIM],
        "sourceIds": ["component-library-source"],
        "contentHash": "2" * 64,
        "label": label,
        "title": title,
        "description": description,
    }
    return KnowledgePiece(**(values | changes))


Entry = tuple[KnowledgePiece, dict[str, Any]]


async def _library(session: AsyncSession) -> None:
    for piece, subject in [*_crafts_own(), *_shared()]:
        session.add(piece)
        await session.flush()
        if subject:
            session.add(KnowledgePieceSubject(pieceId=piece.id, **subject))
            await session.flush()


def _crafts_own() -> list[Entry]:
    return [
        (_component(OWN, "Alum mordant", "Alum binds madder to cotton.", craftId=CRAFT), {}),
        (
            _component(SECRET, "House recipe", "The dyer's own measure.", craftId=CRAFT),
            {"kind": "CONCEPT", "conceptId": SECRET_RECIPE},
        ),
        (
            _component(CRAFT_LINKED, "Printers' route", "Where the printers moved.", facet="HISTORY"),
            {"kind": "CRAFT", "craftId": CRAFT},
        ),
        (
            _component(
                OTHER_TIMELINE, "Timeline", "Another craft's dates.", craftId=OTHER_CRAFT, facet="HISTORY"
            ),
            {},
        ),
    ]


def _shared() -> list[Entry]:
    return [
        (
            _component(
                INDIGO_PLAYER, "Indigo reduction player", "Blue indigo turns soluble and yellow-green."
            ),
            {"kind": "CONCEPT", "conceptId": INDIGO_REDUCTION},
        ),
        (
            _component(
                TANNIN_MOLECULE, "Tannic acid molecule", "The tannin of myrobalan in three dimensions."
            ),
            {"kind": "COMPOUND", "compoundId": TANNIC_ACID},
        ),
        (
            _component(ALUM_CRYSTAL, "Alum crystal", "Potash alum as it is sold.", facet="MATERIALS"),
            {"kind": "CONCEPT", "conceptId": ALUM},
        ),
        (
            _component(LACQUER_CURING, "Lacquer curing", "Lacquer hardens as it oxidises."),
            {"kind": "CONCEPT", "conceptId": LACQUER},
        ),
        (
            _component("shared/chemistry/hidden-one", "Hidden", "Alum, hidden.", hiddenAt=HIDDEN_AT),
            {"kind": "CONCEPT", "conceptId": ALUM},
        ),
    ]


async def test_a_craft_lists_its_own_and_the_shared_components_that_apply_to_it(
    session: AsyncSession,
) -> None:
    await _library(session)
    listed = {item.label: item for item in (await library_components(session, slug=SLUG)).components}
    assert sorted(listed) == sorted([OWN, SECRET, INDIGO_PLAYER, TANNIN_MOLECULE, ALUM_CRYSTAL, CRAFT_LINKED])
    assert listed[OWN].craft_slug == SLUG and listed[OWN].subjects == []
    assert listed[INDIGO_PLAYER].craft_slug is None
    assert listed[INDIGO_PLAYER].subjects == [
        ComponentSubject(kind="CONCEPT", key=str(INDIGO_REDUCTION), name="Indigo reduction")
    ]
    assert listed[TANNIN_MOLECULE].subjects == [
        ComponentSubject(kind="COMPOUND", key=str(TANNIC_ACID), name="Tannic acid")
    ]
    assert listed[CRAFT_LINKED].subjects == [
        ComponentSubject(kind="CRAFT", key=SLUG, name="Component Library Test Craft")
    ]


async def test_a_restricted_concept_is_never_named_as_a_subject(session: AsyncSession) -> None:
    await _library(session)
    listed = {item.label: item for item in (await library_components(session, slug=SLUG)).components}
    assert listed[SECRET].subjects == []


async def test_field_and_kind_narrow_the_library(session: AsyncSession) -> None:
    await _library(session)
    materials = await library_components(session, slug=SLUG, field="MATERIALS")
    assert [item.label for item in materials.components] == [ALUM_CRYSTAL]
    assert (await library_components(session, slug=SLUG, kind="map")).components == []


async def test_words_find_components_by_title_and_description_closest_first(session: AsyncSession) -> None:
    await _library(session)
    found = await library_components(session, query="indigo reduction")
    assert found.components[0].label == INDIGO_PLAYER
    assert found.query == "indigo reduction"
    assert [item.label for item in (await library_components(session, query="lacquer")).components] == [
        LACQUER_CURING
    ]
    assert (await library_components(session, query="zz")).components == []


async def test_an_unknown_craft_is_refused(session: AsyncSession) -> None:
    with pytest.raises(InvalidInput):
        await library_components(session, slug="No-Such-Component-Craft")
