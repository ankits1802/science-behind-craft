import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import Concept, Craft, KnowledgePiece, KnowledgePieceSubject, Source
from app.research.crafts import CraftRef
from app.services.answer_catalogue import section_catalogue

pytestmark = pytest.mark.db

SLUG = "Answer-Catalogue-Test-Craft"
CRAFT = uuid.UUID("ac0c0000-0000-4000-8000-000000000001")
OTHER_CRAFT = uuid.UUID("ac0c0000-0000-4000-8000-000000000002")
INDIGO = uuid.UUID("ac0c0000-0000-4000-8000-000000000003")
OPEN_SOURCE = uuid.UUID("ac0c0000-0000-4000-8000-000000000004")
CLOSED_SOURCE = uuid.UUID("ac0c0000-0000-4000-8000-000000000005")
CLAIM = uuid.UUID("ac0c0000-0000-4000-8000-000000000006")
QUESTION = "Why does the indigo vat turn the cloth blue?"

PLAYER = "answer-catalogue-test-craft/chemistry/indigo-vat-player"
MOLECULE = "shared/chemistry/answer-catalogue-indigo-3d"
CLOSED = "answer-catalogue-test-craft/chemistry/indigo-closed-chart"
NO_PAGE = "answer-catalogue-test-craft/chemistry/indigo-loose-diagram"
HISTORY = "answer-catalogue-test-craft/history/indigo-trade-map"
ELSEWHERE = "answer-catalogue-other-craft/chemistry/indigo-vat-player"
PAGE = {"monograph": SLUG, "anchor": "#rp-blue", "chapter": "chemistry", "units": []}


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
    session.add(Craft(id=CRAFT, name="Answer Catalogue Test Craft", slug=SLUG))
    session.add(
        Craft(id=OTHER_CRAFT, name="Answer Catalogue Other Craft", slug="Answer-Catalogue-Other-Craft")
    )
    session.add(Concept(id=INDIGO, craftId=CRAFT, type="MATERIAL", name="Indigo"))
    session.add(Source(id=OPEN_SOURCE, kind="BOOK", title="Indigo dyeing in Kutch"))
    session.add(
        Source(id=CLOSED_SOURCE, kind="BOOK", title="A closed dyer's notebook", sensitivity="RESTRICTED")
    )
    await session.flush()


def _component(label: str, kind: str, description: str, **changes: Any) -> KnowledgePiece:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "craftId": CRAFT,
        "kind": kind,
        "facet": "CHEMISTRY",
        "topicKey": f"monograph:{label}",
        "language": "en",
        "depth": "EXPERT",
        "payload": PAGE,
        "claimIds": [CLAIM],
        "sourceIds": [str(OPEN_SOURCE)],
        "contentHash": "3" * 64,
        "label": label,
        "title": description.split(".")[0],
        "description": description,
    }
    return KnowledgePiece(**(values | changes))


async def _library(session: AsyncSession, *extra: KnowledgePiece) -> None:
    shared = _component(
        MOLECULE,
        "molecule_3d",
        "Indigo and leucoindigo in three dimensions.",
        craftId=None,
        payload={**PAGE, "anchor": '[class="mols"]'},
    )
    pieces = [
        _component(PLAYER, "reaction_player", "Indigo turns soluble in the vat and blue in the air."),
        shared,
        _component(CLOSED, "chart", "Indigo dips counted.", sourceIds=[str(CLOSED_SOURCE)]),
        _component(NO_PAGE, "diagram", "Indigo drawn loose.", payload={}),
        _component(HISTORY, "map_layer", "Indigo traded by sea.", facet="HISTORY"),
        _component(ELSEWHERE, "reaction_player", "Indigo vat elsewhere.", craftId=OTHER_CRAFT),
        *extra,
    ]
    for piece in pieces:
        session.add(piece)
        await session.flush()
    session.add(KnowledgePieceSubject(pieceId=shared.id, kind="CONCEPT", conceptId=INDIGO))
    await session.flush()


async def test_a_section_is_offered_its_craft_s_own_and_shared_components_with_page_and_sources(
    session: AsyncSession,
) -> None:
    await _library(session)
    catalogue = await section_catalogue(session, craft_slug=SLUG, field="CHEMISTRY", question=QUESTION)
    entries = {entry.label: entry for entry in catalogue.entries}
    assert sorted(entries) == sorted([PLAYER, MOLECULE])
    player = entries[PLAYER]
    page = CraftRef(slug=SLUG, name="Answer Catalogue Test Craft", path="/crafts/Answer-Catalogue-Test-Craft")
    assert (player.kind, player.craft, player.anchor) == ("reaction_player", page, "#rp-blue")
    assert list(player.sources) == [str(OPEN_SOURCE)]
    assert player.sources[str(OPEN_SOURCE)]["title"] == "Indigo dyeing in Kutch"
    assert entries[MOLECULE].craft == page
    (block,) = catalogue.placed([MOLECULE], section_id="s2", first=3).blocks
    assert (block.id, block.href, block.component_kind) == (
        "s2.b3",
        "/crafts/Answer-Catalogue-Test-Craft",
        "molecule_3d",
    )


async def test_a_component_on_a_restricted_source_or_without_a_page_is_never_offered(
    session: AsyncSession,
) -> None:
    await _library(session)
    catalogue = await section_catalogue(
        session, craft_slug=SLUG, field="CHEMISTRY", question="indigo dips drawn"
    )
    labels = [entry.label for entry in catalogue.entries]
    assert CLOSED not in labels
    assert NO_PAGE not in labels
    assert ELSEWHERE not in labels


async def test_the_section_s_field_and_the_question_s_words_narrow_the_catalogue(
    session: AsyncSession,
) -> None:
    await _library(session)
    history = await section_catalogue(session, craft_slug=SLUG, field="HISTORY", question="indigo trade")
    assert [entry.label for entry in history.entries] == [HISTORY]
    assert (await section_catalogue(session, craft_slug=SLUG, field="CHEMISTRY", question="zz")).entries == ()


async def test_at_most_six_components_are_offered(session: AsyncSession) -> None:
    more = [
        _component(f"answer-catalogue-test-craft/chemistry/indigo-step-{n}", "diagram", f"Indigo step {n}.")
        for n in range(8)
    ]
    await _library(session, *more)
    catalogue = await section_catalogue(session, craft_slug=SLUG, field="CHEMISTRY", question="indigo")
    assert len(catalogue.entries) == 6
    assert len(catalogue.options()) == 6
