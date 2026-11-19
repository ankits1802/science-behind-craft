import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ArticleSection,
    Claim,
    ClaimSource,
    Compound,
    Concept,
    Craft,
    CraftCategory,
    CuratedCategoryClaim,
    CuratedClaim,
    KnowledgePiece,
    KnowledgePieceSubject,
    Source,
)
from app.research.monograph_page import MonographContent
from app.services.component_library import library_components
from app.services.monograph_load import load_monograph

from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 19, 12, tzinfo=UTC)
SLUG = "Monograph-Load-Test-Craft"
CRAFT = uuid.UUID("40a0f000-0000-4000-8000-000000000001")
ALUM = uuid.UUID("40a0f000-0000-4000-8000-000000000002")
SOURCE = uuid.UUID("40a0f000-0000-4000-8000-000000000003")
FACT = uuid.UUID("40a0f000-0000-4000-8000-000000000004")
PLAYER = "monograph-load-test-craft/chemistry/alum-player"
CHART = "shared/chemistry/unsourced-chart"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        opened.add(Craft(id=CRAFT, name="Monograph Load Test Craft", slug=SLUG))
        opened.add(Source(id=SOURCE, kind="PAPER", title="Alum mordants", licence="CC-BY-4.0", year=2019))
        opened.add(Compound(name="Indigo", pubchemCid=10215))
        await opened.flush()
        opened.add(Concept(id=ALUM, craftId=CRAFT, type="MATERIAL", name="Alum"))
        await opened.flush()
        opened.add(
            Claim(
                id=FACT,
                subjectType="CONCEPT",
                subjectId=ALUM,
                predicate="states",
                text="Alum fixes the madder red.",
                evidenceLevel="PROVISIONAL",
                origin="IMPORT",
                field="CHEMISTRY",
            )
        )
        await opened.flush()
        opened.add(CuratedClaim(claimId=FACT, craftId=CRAFT, key="C001", discipline="CHEMISTRY"))
        opened.add(ClaimSource(claimId=FACT, sourceId=SOURCE, quote="alum fixes the red", relation="DIRECT"))
        await opened.flush()
        yield opened


def _cited(text: str, key: str, word: str) -> dict[str, Any]:
    return {"m": "s", "c": [text, {"m": "cite", "key": key, "g": ["g1"], "c": [word]}]}


UNIT = {"chapter": "chemistry", "field": "CHEMISTRY", "claimIds": []}
COMPONENT = {"chapter": "chemistry", "title": "T", "description": "D.", "field": "CHEMISTRY", "fields": []}
SOURCE_ROW = {
    "number": 1,
    "title": "Alum mordants",
    "fullTitle": None,
    "publisher": None,
    "year": 2019,
    "grade": "A",
    "url": None,
    "extra": None,
    "dossierSourceId": "S01",
}


def _units(first: str) -> dict[str, Any]:
    return {
        "u1": UNIT | {"tag": "h3", "nodes": ["The red"]},
        "u2": UNIT | {"tag": "p", "nodes": [_cited(first, "k1", "red."), _cited("A new ", "k2", "claim.")]},
        "u3": UNIT | {"tag": "p", "nodes": [_cited("Only a new ", "k2", "claim.")]},
    }


def _components() -> list[dict[str, Any]]:
    player_subjects = [f"craft:{SLUG}", "compound:10215", "concept:alum", "place:lgd:449"]
    return [
        COMPONENT
        | {"label": PLAYER, "anchor": "#red", "kind": "reaction_player", "subjects": player_subjects},
        COMPONENT | {"label": CHART, "anchor": "#chart", "kind": "chart", "subjects": []},
    ]


def _layout() -> list[dict[str, Any]]:
    entry = {"chapter": "chemistry"}
    return [
        entry | {"kind": "unit", "ref": "u1"},
        entry | {"kind": "component", "ref": PLAYER},
        entry | {"kind": "unit", "ref": "u2", "within": PLAYER},
        entry | {"kind": "component", "ref": CHART},
        entry | {"kind": "unit", "ref": "u3", "within": CHART},
    ]


def _content(first: str = "Alum fixes the ") -> MonographContent:
    return MonographContent.model_validate(
        {
            "craftSlug": SLUG,
            "sources": {"g1": SOURCE_ROW},
            "citations": {
                "k1": [{"source": "g1", "locator": "p. 4", "quote": "alum fixes the red"}],
                "k2": [],
            },
            "citationClaims": {"k1": ["C001"], "k2": ["C999"]},
            "data": {},
            "units": _units(first),
            "components": _components(),
            "layout": _layout(),
        }
    )


async def _sections(session: AsyncSession) -> list[tuple[int, str, list[Any]]]:
    rows = await session.scalars(
        select(ArticleSection).where(ArticleSection.craftId == CRAFT).order_by(ArticleSection.version)
    )
    return [(row.version, row.status, row.sentences) for row in rows]


async def test_cited_sentences_with_stored_facts_become_the_published_section(session: AsyncSession) -> None:
    loaded = await load_monograph(session, _content(), now=NOW)
    assert (loaded.sections_written, loaded.sentences, loaded.sentences_awaiting_facts) == (
        ["CHEMISTRY"],
        1,
        2,
    )
    assert await _sections(session) == [
        (1, "PUBLISHED", [{"text": "Alum fixes the red.", "claimIds": [str(FACT)]}])
    ]


async def test_a_component_resting_on_stored_facts_is_registered_with_its_subjects(
    session: AsyncSession,
) -> None:
    loaded = await load_monograph(session, _content(), now=NOW)
    assert loaded.components_written == [PLAYER] and loaded.components_awaiting_facts == [CHART]
    assert loaded.unresolved_subjects == ["concept:alum"]
    piece = await session.scalar(select(KnowledgePiece).where(KnowledgePiece.label == PLAYER))
    assert piece is not None
    assert (piece.kind, piece.craftId, piece.claimIds, piece.sourceIds) == (
        "reaction_player",
        CRAFT,
        [FACT],
        [str(SOURCE)],
    )
    kinds = await session.scalars(
        select(KnowledgePieceSubject.kind).where(KnowledgePieceSubject.pieceId == piece.id)
    )
    assert sorted(kinds) == ["COMPOUND", "CRAFT", "PLACE"]
    listed = await library_components(session, slug=SLUG)
    assert [item.label for item in listed.components] == [PLAYER]


async def test_loading_again_changes_nothing_and_a_changed_sentence_supersedes_the_section(
    session: AsyncSession,
) -> None:
    await load_monograph(session, _content(), now=NOW)
    again = await load_monograph(session, _content(), now=NOW)
    assert (again.sections_unchanged, again.components_unchanged) == (["CHEMISTRY"], 1)
    changed = await load_monograph(session, _content("Alum, a mordant, fixes the "), now=NOW)
    assert changed.sections_written == ["CHEMISTRY"] and changed.components_unchanged == 1
    assert [(version, status) for version, status, _ in await _sections(session)] == [
        (1, "SUPERSEDED"),
        (2, "PUBLISHED"),
    ]


async def _cross_seed(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    category, kin = uuid.uuid4(), uuid.uuid4()
    session.add(
        CraftCategory(
            id=category,
            slug="Monograph-Load-Test-Category",
            name="Monograph Load Test Category",
            sortOrder=999,
        )
    )
    session.add(Craft(id=kin, name="Monograph Load Kin Craft", slug="Monograph-Load-Kin-Craft"))
    await session.flush()
    shared, theirs = uuid.uuid4(), uuid.uuid4()
    for claim_id, text in (
        (shared, "Alum binds madder in every block print."),
        (theirs, "The kin craft prints at dawn."),
    ):
        session.add(
            Claim(
                id=claim_id,
                subjectType="CONCEPT",
                subjectId=ALUM,
                predicate="states",
                text=text,
                evidenceLevel="PROVISIONAL",
                origin="IMPORT",
                field="CHEMISTRY",
            )
        )
    await session.flush()
    session.add(CuratedCategoryClaim(claimId=shared, categoryId=category, key="C010", discipline="CHEMISTRY"))
    session.add(CuratedClaim(claimId=theirs, craftId=kin, key="C001", discipline="CHEMISTRY"))
    for claim_id in (shared, theirs):
        session.add(
            ClaimSource(claimId=claim_id, sourceId=SOURCE, quote="alum fixes the red", relation="DIRECT")
        )
    await session.flush()
    return shared, theirs


async def test_a_category_fact_joins_the_section_and_another_crafts_fact_only_rests_a_component(
    session: AsyncSession,
) -> None:
    shared, theirs = await _cross_seed(session)
    content = _content().model_dump(by_alias=True)
    content["citationClaims"] |= {
        "k1": ["category:Monograph-Load-Test-Category:C010"],
        "k2": ["craft:Monograph-Load-Kin-Craft:C001"],
    }
    loaded = await load_monograph(session, MonographContent.model_validate(content), now=NOW)
    assert await _sections(session) == [
        (1, "PUBLISHED", [{"text": "Alum fixes the red.", "claimIds": [str(shared)]}])
    ]
    assert loaded.components_written == [PLAYER, CHART]
    chart = await session.scalar(select(KnowledgePiece).where(KnowledgePiece.label == CHART))
    assert chart is not None and chart.claimIds == [theirs] and chart.craftId is None
