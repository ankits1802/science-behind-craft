import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Claim,
    Concept,
    ConceptEdge,
    Craft,
    KnowledgePiece,
    KnowledgePieceSubject,
    Material,
    Process,
    ProcessStage,
    Term,
    TermConcept,
)
from app.services.orphan_concepts import OrphanConcept, orphan_concepts, remove_orphan_concepts, sweep_orphans

from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

NOW = datetime.now(UTC)
WEEKS_AGO = NOW - timedelta(days=10)
YESTERDAY = NOW - timedelta(days=1)
CRAFT = uuid.UUID("0e1f0000-0000-4000-8000-000000000001")
PROCESS = uuid.UUID("0e1f0000-0000-4000-8000-000000000002")
NAMES = ("lone", "claimed", "edged", "staged", "material", "pieced", "termed", "curated", "young")
IDS = {name: uuid.UUID(f"0e1f0000-0000-4000-8000-1000000000{n:02d}") for n, name in enumerate(NAMES, start=1)}
LINKED = ("claimed", "edged", "staged", "material", "pieced", "termed")


def concept(name: str) -> Concept:
    return Concept(
        id=IDS[name],
        craftId=CRAFT,
        type="MATERIAL",
        name=f"Orphan test {name}",
        originRef="curation:Orphan-Test-Craft:K1" if name == "curated" else "live_research",
        createdAt=YESTERDAY if name == "young" else WEEKS_AGO,
    )


async def links(session: AsyncSession) -> None:
    session.add(
        Claim(
            subjectType="CONCEPT",
            subjectId=IDS["claimed"],
            predicate="states",
            text="A claim about the concept.",
            evidenceLevel="PROVISIONAL",
            origin="IMPORT",
        )
    )
    session.add(ConceptEdge(srcId=IDS["edged"], dstId=IDS["curated"], relation="USES"))
    session.add(Process(id=PROCESS, craftId=CRAFT, name="Orphan test process"))
    await session.flush()
    session.add(ProcessStage(processId=PROCESS, ordinal=1, name="Orphan test stage", conceptId=IDS["staged"]))
    session.add(Material(name="Orphan test alum", nameNorm="orphan test alum", conceptId=IDS["material"]))
    term = Term(key="orphan-test-term", label="Orphan test term")
    piece = KnowledgePiece(
        kind="prose",
        facet="CHEMISTRY",
        topicKey="orphan-test:piece",
        language="en",
        depth="EXPERT",
        payload={},
        claimIds=[uuid.uuid4()],
        sourceIds=["orphan-test-source"],
        contentHash="3" * 64,
    )
    session.add_all([term, piece])
    await session.flush()
    session.add(TermConcept(termId=term.id, conceptId=IDS["termed"]))
    session.add(KnowledgePieceSubject(pieceId=piece.id, kind="CONCEPT", conceptId=IDS["pieced"]))
    await session.flush()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        opened.add(Craft(id=CRAFT, name="Orphan Test Craft", slug="Orphan-Test-Craft"))
        await opened.flush()
        opened.add_all([concept(name) for name in NAMES])
        await opened.flush()
        await links(opened)
        yield opened


async def standing(session: AsyncSession) -> set[str]:
    found = set(await session.scalars(select(Concept.id).where(Concept.id.in_(IDS.values()))))
    return {name for name, concept_id in IDS.items() if concept_id in found}


async def test_only_an_old_unlinked_research_concept_is_an_orphan(session: AsyncSession) -> None:
    found = await orphan_concepts(session, now=NOW, limit=100_000)
    assert [orphan.concept_id for orphan in found if orphan.concept_id in IDS.values()] == [IDS["lone"]]


async def test_an_orphan_is_reported_first_and_removed_the_next_night(session: AsyncSession) -> None:
    first = await sweep_orphans(session, now=NOW)
    assert str(IDS["lone"]) in first.reported
    assert await standing(session) == set(NAMES)
    second = await sweep_orphans(session, now=NOW + timedelta(days=1))
    assert second.removed >= 1
    assert await standing(session) == set(NAMES) - {"lone"}


async def test_a_linked_curated_or_young_concept_is_never_removed_even_when_named(
    session: AsyncSession,
) -> None:
    named = [OrphanConcept(IDS[name], name, "MATERIAL", CRAFT) for name in NAMES if name != "lone"]
    assert await remove_orphan_concepts(session, named, now=NOW) == 0
    assert await standing(session) == set(NAMES)
    assert set(LINKED) <= await standing(session)
