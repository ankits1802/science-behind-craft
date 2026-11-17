import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.curation.check_file import check_file_text, verified_digest
from app.curation.checks import content_problems, default_context
from app.curation.dossier import Dossier
from app.models import (
    Claim,
    ClaimSource,
    Concept,
    ConceptEdge,
    CraftGiRecord,
    CraftLocation,
    CraftPrice,
    CraftWorkforce,
    CuratedClaim,
    CuratedCraft,
    EnvDataset,
    KnowledgePiece,
    Process,
    ProcessStage,
    Reaction,
    ReviewEvent,
    RiverBasin,
    Source,
)
from app.research.craft_page import CraftPage
from app.retrieval.statements import EVERY_CRAFT, claim_conditions
from app.services import knowledge_view
from app.services.craft_page import craft_page
from app.services.craft_page_records import craft_page_records
from app.services.curation_import import ImportReport, import_curation
from app.services.curation_keys import CURATED_PROCESS_VARIANT, curated_id
from app.services.place_offers import mapped_districts, region_offer

from ..contracts.golden import golden_json
from ..curation.import_support import AJRAKH, AJRAKH_GOLDEN, checked
from .test_place_db import HYDRORIVERS, store_datasets, store_rivers

pytestmark = pytest.mark.db

KACHCHH = 449
SEED_EDGE_SENTENCES = 557
EDGE_FILLER = "Sequential order in the GI method of production."
CURATED_PARTS = (
    "curation",
    "overview",
    "sources_differ",
    "places",
    "communities",
    "process",
    "glossary",
    "pictures",
    "open_questions",
)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            yield session
            await session.close()
        finally:
            await transaction.rollback()


async def count(session: AsyncSession, *conditions: Any, model: Any = Claim) -> int:
    return (await session.execute(select(func.count()).select_from(model).where(*conditions))).scalar_one()


async def ajrakh_id(session: AsyncSession) -> uuid.UUID:
    craft = await knowledge_view.resolve_craft(session, AJRAKH)
    assert craft is not None
    return craft.id


def imported(report: ImportReport, slug: str) -> Any:
    assert report.refused == [], [outcome.problems for outcome in report.refused]
    return next(outcome for outcome in report.dossiers if outcome.craft_slug == slug)


async def test_the_kutch_ajrakh_dossier_imports_in_full(session: AsyncSession) -> None:
    outcome = imported(await import_curation(session), AJRAKH)
    assert outcome.status == "IMPORTED" and outcome.version == 1
    craft_id = await ajrakh_id(session)
    curated = select(CuratedClaim.claimId).where(CuratedClaim.craftId == craft_id)
    assert await count(session, Claim.id.in_(curated)) == 132
    assert await count(session, Claim.id.in_(curated), Claim.status != "APPROVED") == 0
    assert await count(session, ClaimSource.claimId.in_(curated), model=ClaimSource) == 269
    locations = (
        (await session.execute(select(CraftLocation).where(CraftLocation.craftId == craft_id)))
        .scalars()
        .all()
    )
    assert {(row.districtLgd, row.stateLgd) for row in locations} == {(KACHCHH, 24), (90, 8)}
    assert {row.role for row in locations} == {"PRACTISED", "HISTORIC_CENTRE", "MIGRATED_FROM", "MIGRATED_TO"}
    stages = await session.execute(
        select(ProcessStage.ordered, func.count())
        .where(ProcessStage.id.in_(_curated_stages(craft_id)))
        .group_by(ProcessStage.ordered)
    )
    assert dict(stages.tuples().all()) == {True: 11, False: 3}
    assert await count(session, Reaction.stageId.in_(_curated_stages(craft_id)), model=Reaction) == 2
    assert (
        await count(
            session,
            KnowledgePiece.craftId == craft_id,
            KnowledgePiece.createdFromAnswerId.is_(None),
            model=KnowledgePiece,
        )
        >= 8
    )
    gi = (await session.execute(select(CraftGiRecord).where(CraftGiRecord.craftId == craft_id))).scalar_one()
    assert (gi.applicationNumber, gi.registeredOn) == ("1050", "2024-04-22")
    assert await count(session, CraftWorkforce.craftId == craft_id, model=CraftWorkforce) == 5
    assert await count(session, CraftPrice.craftId == craft_id, model=CraftPrice) == 1


def _curated_stages(craft_id: uuid.UUID) -> Any:
    processes = select(Process.id).where(
        Process.craftId == craft_id, Process.variant == CURATED_PROCESS_VARIANT
    )
    return select(ProcessStage.id).where(ProcessStage.processId.in_(processes))


async def test_the_served_page_matches_the_golden_fixture(session: AsyncSession) -> None:
    imported(await import_curation(session), AJRAKH)
    craft = await knowledge_view.resolve_craft(session, AJRAKH)
    assert craft is not None
    page = craft_page(await craft_page_records(session, craft))
    golden = CraftPage.model_validate(golden_json(AJRAKH_GOLDEN))
    for part in CURATED_PARTS:
        assert getattr(page, part) == getattr(golden, part), part
    served = {claim.id: claim for claim in page.claims}
    assert all(served[claim.id] == claim for claim in golden.claims)
    sources = {source.id: source for source in page.sources}
    assert all(sources[source.id] == source for source in golden.sources)


async def test_a_second_import_changes_nothing(session: AsyncSession) -> None:
    await import_curation(session)
    events = await count(session, model=ReviewEvent)
    rows = await _curated_rows(session)
    again = await import_curation(session)
    assert again.withdrawn_edges == 0
    assert [outcome.changed for outcome in again.dossiers] == [{} for _ in again.dossiers]
    assert await count(session, model=ReviewEvent) == events
    assert await _curated_rows(session) == rows


async def _curated_rows(session: AsyncSession) -> list[Any]:
    statement = (
        select(Claim.id, Claim.text, Claim.status, Claim.evidenceLevel, Claim.version, Claim.sourcesDiffer)
        .join(CuratedClaim, CuratedClaim.claimId == Claim.id)
        .order_by(Claim.id)
    )
    return list((await session.execute(statement)).tuples().all())


def droppable_version(directory: Path) -> str:
    result = checked(AJRAKH)
    assert result.dossier is not None and result.check is not None
    context = default_context()
    for claim in result.dossier.claims:
        plain = json.loads(result.dossier.model_dump_json(by_alias=True))
        plain["version"] = 2
        plain["claims"] = [row for row in plain["claims"] if row["id"] != claim.id]
        try:
            later = Dossier.model_validate(plain)
        except ValueError:
            continue
        if content_problems(later, context):
            continue
        check = result.check.model_copy(
            update={
                "dossier_version": 2,
                "dossier_digest": verified_digest(later),
                "quotes": [entry for entry in result.check.quotes if entry.claim_id != claim.id],
            }
        )
        (directory / f"{AJRAKH}.json").write_text(
            later.model_dump_json(by_alias=True, indent=2), encoding="utf-8"
        )
        (directory / f"{AJRAKH}.check.json").write_text(check_file_text(check), encoding="utf-8")
        return claim.id
    raise AssertionError("no claim of the dossier can be dropped on its own")


async def test_a_new_version_supersedes_a_dropped_claim_and_keeps_its_citations(
    session: AsyncSession, tmp_path: Path
) -> None:
    imported(await import_curation(session), AJRAKH)
    dropped = curated_id(AJRAKH, droppable_version(tmp_path))
    citations = await count(session, ClaimSource.claimId == dropped, model=ClaimSource)
    assert citations >= 1
    outcome = imported(await import_curation(session, directory=tmp_path), AJRAKH)
    assert outcome.version == 2
    claim = (await session.execute(select(Claim).where(Claim.id == dropped))).scalar_one()
    assert claim.status == "SUPERSEDED"
    assert await count(session, ClaimSource.claimId == dropped, model=ClaimSource) == citations
    assert await count(session, CuratedClaim.claimId == dropped, model=CuratedClaim) == 1
    assert (
        await count(
            session, ReviewEvent.claimId == dropped, ReviewEvent.toStatus == "SUPERSEDED", model=ReviewEvent
        )
        == 1
    )
    views, _ = await knowledge_view.claims_by_id(session, [dropped])
    assert views == {}
    craft_id = await ajrakh_id(session)
    version = await session.scalar(select(CuratedCraft.version).where(CuratedCraft.craftId == craft_id))
    assert version == 2


async def test_seed_edge_sentences_leave_every_reader_surface(session: AsyncSession) -> None:
    edges = list((await session.scalars(select(Claim.id).where(Claim.subjectType == "EDGE"))).all())
    linked = await count(session, ConceptEdge.claimId.is_not(None), model=ConceptEdge)
    report = await import_curation(session)
    assert len(edges) == report.withdrawn_edges == SEED_EDGE_SENTENCES
    assert await count(session, Claim.id.in_(edges), Claim.status != "WITHDRAWN") == 0
    assert await count(
        session, ReviewEvent.claimId.in_(edges), ReviewEvent.systemActor == "curation", model=ReviewEvent
    ) == len(edges)
    assert await count(session, ConceptEdge.claimId.is_not(None), model=ConceptEdge) == linked
    assert await count(session, Claim.id.in_(edges), *claim_conditions(EVERY_CRAFT, mode="DEEP")) == 0
    views, _ = await knowledge_view.claims_by_id(session, edges)
    assert views == {}
    for slug in (AJRAKH, "Bagru-Hand-Block-Print"):
        craft = await knowledge_view.resolve_craft(session, slug)
        assert craft is not None
        page = craft_page(await craft_page_records(session, craft))
        assert EDGE_FILLER not in {claim.text for claim in page.claims}
        assert set(edges).isdisjoint(claim.id for claim in page.claims)


async def test_claims_written_by_answers_are_never_edited(session: AsyncSession) -> None:
    craft_id = await ajrakh_id(session)
    concept = await session.scalar(
        select(Concept.id)
        .where(Concept.craftId == craft_id, Concept.originRef.like("ie:%"), Concept.sensitivity == "OPEN")
        .limit(1)
    )
    source = await session.scalar(select(Source.id).where(Source.sensitivity == "OPEN").limit(1))
    answer = uuid.uuid4()
    session.add(
        Claim(
            id=answer,
            subjectType="CONCEPT",
            subjectId=concept,
            predicate="states",
            text="Ajrakh cloth was traded from Kutch to Sindh along the old caravan routes.",
            evidenceLevel="PROVISIONAL",
            origin="LIVE_RESEARCH",
            status="APPROVED",
        )
    )
    await session.flush()
    session.add(
        ClaimSource(
            claimId=answer, sourceId=source, quote="traded along the caravan routes", quoteCheck="PASS"
        )
    )
    await session.flush()
    before = (
        await session.execute(select(Claim.text, Claim.status, Claim.version).where(Claim.id == answer))
    ).one()
    imported(await import_curation(session), AJRAKH)
    after = (
        await session.execute(select(Claim.text, Claim.status, Claim.version).where(Claim.id == answer))
    ).one()
    assert after == before
    craft = await knowledge_view.resolve_craft(session, AJRAKH)
    assert craft is not None
    page = craft_page(await craft_page_records(session, craft))
    assert {claim.id: claim.provenance for claim in page.claims}[answer] == "FROM_ANSWERS"


async def test_imported_places_reach_the_region_builder(session: AsyncSession) -> None:
    await session.execute(delete(RiverBasin))
    await session.execute(delete(EnvDataset))
    ids = await store_datasets(session)
    await store_rivers(session, ids[HYDRORIVERS])
    await session.flush()
    imported(await import_curation(session), AJRAKH)
    craft = await knowledge_view.resolve_craft(session, AJRAKH)
    assert craft is not None
    assert KACHCHH in await mapped_districts(session, craft)
    offer = await region_offer(session, AJRAKH)
    assert offer is not None and KACHCHH in offer.craft_districts
    assert offer.rivers and all(KACHCHH in river.trace.district_lgds for river in offer.rivers)
