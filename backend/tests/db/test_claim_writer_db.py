import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Answer,
    Chunk,
    Claim,
    ClaimSource,
    Concept,
    Craft,
    ReviewEvent,
    Source,
    UsageEvent,
)
from app.providers.router import tagged_spend
from app.research.composition import ComposedSentence, QuotedSpan
from app.research.write_back import ClaimWriteBack
from app.services.answering import AnswerAsk
from app.services.claim_writer import SqlClaimWriter, write_back_claim_id
from app.services.coverage_selection import least_covered_crafts
from app.services.knowledge_view import claims_for
from app.services.live_source_store import keep_document, live_source_id
from app.sources.adapter import build_document

from ..composer.fixtures import ABSTRACT_ITEM, LONG_ITEM, LONG_TEXT
from ..research.fixtures import RETRIEVED
from .write_back_seed import (
    ABSTRACT_ID,
    ALUM_CONCEPT,
    ANSWER,
    CRAFT,
    FIGURE_QUOTE,
    FIGURE_TEXT,
    IMPORTED,
    PAGE_ID,
    STAGE_CONCEPT,
    WASH_QUOTE,
    WASH_TEXT,
    ZELVAR,
    answer,
    answer_store,
    expected_claim_id,
    said,
    seeded_session,
    write,
    zelvar_pack,
)

pytestmark = pytest.mark.db


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in seeded_session():
        yield opened


async def citations(session: AsyncSession, claim_id: uuid.UUID) -> list[ClaimSource]:
    rows = await session.scalars(
        select(ClaimSource).where(ClaimSource.claimId == claim_id).order_by(ClaimSource.id)
    )
    return list(rows)


async def test_a_write_back_keeps_each_read_document_with_embedded_chunks(session: AsyncSession) -> None:
    stored = await write(session, answer(said(FIGURE_TEXT, ABSTRACT_ID, FIGURE_QUOTE)))
    page_id = live_source_id(LONG_ITEM.source_key)
    assert stored.source_ids == (IMPORTED, page_id)
    imported = await session.get(Source, IMPORTED)
    assert (imported.origin, imported.title) == ("IMPORT", "Imported lake paper")
    kept = await session.scalars(select(Chunk.text).where(Chunk.sourceId == IMPORTED))
    assert list(kept) == ["Curated imported text about lakes."]
    page = await session.get(Source, page_id)
    assert (page.origin, page.storage, page.reliability, page.retrievedAt) == (
        "LIVE_RESEARCH",
        "FULL_TEXT",
        "C",
        RETRIEVED,
    )
    page_chunks = list(await session.scalars(select(Chunk).where(Chunk.sourceId == page_id)))
    assert page_chunks and all(c.embedding is not None and c.acl == "RESEARCHER" for c in page_chunks)


async def test_a_write_back_stores_a_cited_claim_with_its_provenance(session: AsyncSession) -> None:
    stored = await write(session, answer(said(FIGURE_TEXT, ABSTRACT_ID, FIGURE_QUOTE)))
    claim_id = expected_claim_id("mordant baths held 8 g/l alum and were heated to 60 °c")
    assert [(r.claim_id, r.created) for r in stored.results] == [(claim_id, True)]
    claim = await session.get(Claim, claim_id)
    assert (claim.subjectType, claim.subjectId, claim.evidenceLevel) == (
        "CONCEPT",
        ALUM_CONCEPT,
        "PROVISIONAL",
    )
    assert (claim.origin, claim.status, claim.createdByKind) == ("LIVE_RESEARCH", "APPROVED", "SYSTEM")
    assert claim.embedding is not None
    (cite,) = await citations(session, claim_id)
    assert (cite.sourceId, cite.quote, cite.quoteCheck, cite.relation) == (
        IMPORTED,
        FIGURE_QUOTE,
        "PASS",
        "DIRECT",
    )
    assert (cite.foundBy, cite.answerId, cite.retrievedAt, cite.checkedAt) == (
        "ANSWER",
        ANSWER,
        RETRIEVED,
        RETRIEVED,
    )
    (event,) = await session.scalars(select(ReviewEvent).where(ReviewEvent.claimId == claim_id))
    assert (event.actorKind, event.systemActor, event.toLevel, event.toStatus) == (
        "SYSTEM",
        "live_research",
        "PROVISIONAL",
        "APPROVED",
    )
    assert str(ANSWER) in event.note
    views, _ = await claims_for(session, await session.get(Craft, CRAFT), mode="HYBRID")
    assert claim_id in {view.id for view in views}


async def test_a_quote_links_the_chunk_it_came_from(session: AsyncSession) -> None:
    stored = await write(session, answer(said(WASH_TEXT, PAGE_ID, WASH_QUOTE)))
    (cite,) = await citations(session, stored.results[0].claim_id)
    chunk = await session.get(Chunk, cite.chunkId)
    assert chunk.sourceId == live_source_id(LONG_ITEM.source_key)
    assert WASH_QUOTE in chunk.text
    assert cite.locator == chunk.locator


async def test_the_same_claim_again_adds_only_new_citations(session: AsyncSession) -> None:
    first = await write(session, answer(said(FIGURE_TEXT, ABSTRACT_ID, FIGURE_QUOTE)))
    again = await write(
        session, answer(said(FIGURE_TEXT, ABSTRACT_ID, FIGURE_QUOTE)), found_by="BACKGROUND", answer_id=None
    )
    claim_id = first.results[0].claim_id
    assert [(r.claim_id, r.created) for r in again.results] == [(claim_id, False)]
    assert len(await citations(session, claim_id)) == 1
    page = ComposedSentence(
        text=FIGURE_TEXT,
        evidence_ids=[ABSTRACT_ID, PAGE_ID],
        spans=[QuotedSpan(ref=ABSTRACT_ID, text=FIGURE_QUOTE), QuotedSpan(ref=PAGE_ID, text=WASH_QUOTE)],
    )
    await write(session, answer(page))
    assert [c.sourceId for c in await citations(session, claim_id)].count(
        live_source_id(LONG_ITEM.source_key)
    ) == 1
    assert len(await citations(session, claim_id)) == 2
    count = await session.scalar(select(func.count()).select_from(Claim).where(Claim.id == claim_id))
    assert count == 1


async def test_a_quoted_write_raises_an_inferred_claim_to_provisional(session: AsyncSession) -> None:
    guess = said(WASH_TEXT, PAGE_ID, WASH_QUOTE)
    first = await write(session, answer(guesses=(guess,)))
    claim_id = first.results[0].claim_id
    assert (await session.get(Claim, claim_id)).evidenceLevel == "HYPOTHESIS"
    await write(session, answer(guess))
    claim = await session.get(Claim, claim_id)
    await session.refresh(claim)
    assert claim.evidenceLevel == "PROVISIONAL"
    events = list(await session.scalars(select(ReviewEvent).where(ReviewEvent.claimId == claim_id)))
    assert sorted((e.fromLevel or "", e.toLevel) for e in events) == [
        ("", "HYPOTHESIS"),
        ("HYPOTHESIS", "PROVISIONAL"),
    ]


async def test_a_stage_subject_attaches_to_the_named_stage(session: AsyncSession) -> None:
    document = build_document(LONG_ITEM, LONG_TEXT, "FULL_TEXT")
    await keep_document(session, document)
    claim = ClaimWriteBack.model_validate(
        {
            "craftSlug": ZELVAR.slug,
            "subject": {"conceptType": "PROCESS_STAGE", "conceptName": " mordanting "},
            "predicate": "states",
            "text": WASH_TEXT,
            "label": "QUOTED",
            "levelReason": "test",
            "citations": [
                {
                    "evidence": LONG_ITEM,
                    "quote": LONG_ITEM.quotes[0],
                    "quoteCheck": "PASS",
                    "relation": "DIRECT",
                }
            ],
            "foundBy": "BACKGROUND",
        }
    )
    (result,) = await SqlClaimWriter(session).write([claim])
    assert (await session.get(Claim, result.claim_id)).subjectId == STAGE_CONCEPT
    assert result.claim_id == write_back_claim_id(claim.dedupe_key)


async def test_new_concepts_are_created_once_on_the_craft(session: AsyncSession) -> None:
    base = {
        "craftSlug": ZELVAR.slug,
        "predicate": "states",
        "label": "INFERRED",
        "levelReason": "test",
        "citations": [
            {"evidence": ABSTRACT_ITEM, "quote": None, "quoteCheck": "NA", "relation": "CONTEXTUAL"}
        ],
        "foundBy": "BACKGROUND",
    }
    claims = [
        ClaimWriteBack.model_validate(
            base | {"subject": {"conceptType": "TOOL", "conceptName": name}, "text": text}
        )
        for name, text in (("Wooden block", "Blocks are carved."), ("wooden  block", "Blocks are teak."))
    ]
    results = await SqlClaimWriter(session).write(claims)
    subjects = {(await session.get(Claim, r.claim_id)).subjectId for r in results}
    (subject,) = subjects
    concept = await session.get(Concept, subject)
    assert (concept.craftId, concept.type, concept.originRef) == (CRAFT, "TOOL", "live_research")


async def test_the_least_covered_open_crafts_come_first(session: AsyncSession) -> None:
    await write(session, answer(said(FIGURE_TEXT, ABSTRACT_ID, FIGURE_QUOTE)))
    picked = await least_covered_crafts(session, now=datetime.now(UTC), limit=100_000)
    slugs = [craft.slug for craft in picked]
    assert "Zelvar-Others" not in slugs
    assert "Zelvar-Rested" not in slugs
    assert slugs.index("Zelvar-Quiet") < slugs.index(ZELVAR.slug)
    zelvar = next(craft for craft in picked if craft.slug == ZELVAR.slug)
    assert (zelvar.claims, dict(zelvar.facet_claims)) == (1, {"MATERIAL": 1})


async def test_tagged_spend_sums_only_the_tagged_events_of_the_day(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    since = now - timedelta(hours=1)
    rows = [
        ("enrichment-0001aaaa", Decimal("0.120000"), "OK", now),
        ("enrichment-0002bbbb", Decimal("0.030000"), "OK", now),
        ("enrichment-0003cccc", Decimal("0.500000"), "OK", now - timedelta(days=1)),
        ("answer-request-0001", Decimal("0.700000"), "OK", now),
    ]
    session.add_all(
        UsageEvent(task="PLAN", requestId=tag, costUsd=cost, outcome=outcome, createdAt=at)
        for tag, cost, outcome, at in rows
    )
    await session.flush()
    assert await tagged_spend(session, request_id_prefix="enrichment-", since=since) == Decimal("0.150000")
    assert await tagged_spend(session, request_id_prefix="enrichment-0001", since=since) == Decimal(
        "0.120000"
    )


async def test_an_answer_keeps_its_research_and_cites_what_it_wrote(session: AsyncSession) -> None:
    store = answer_store(session)
    ask = AnswerAsk(question="Why does alum keep Zelvar red?", mode="HYBRID")
    kept = await store.keep(ask, zelvar_pack(), answer(said(FIGURE_TEXT, ABSTRACT_ID, FIGURE_QUOTE)))
    claim_id = expected_claim_id("mordant baths held 8 g/l alum and were heated to 60 °c")
    assert kept.claims_of == ((claim_id,),)
    row = await session.get(Answer, kept.answer_id)
    assert (row.question, row.mode, row.craftId, row.claimIds) == (ask.question, "HYBRID", CRAFT, [claim_id])
    assert row.tiersUsed == ["T0", "T1", "T2", "T3", "T4"]
    (cite,) = await citations(session, claim_id)
    assert (cite.foundBy, cite.answerId) == ("ANSWER", kept.answer_id)
    cited = await store.cited([claim_id])
    view = cited.views[claim_id]
    assert (view.level, view.citations[0]["quote"], view.citations[0]["sourceId"]) == (
        "PROVISIONAL",
        FIGURE_QUOTE,
        str(IMPORTED),
    )
    assert cited.sources[str(IMPORTED)]["title"] == "Imported lake paper"


async def test_verified_answers_read_only_reviewed_and_verified_claims(session: AsyncSession) -> None:
    store = answer_store(session)
    await store.keep(
        AnswerAsk(question="Why alum?", mode="HYBRID"),
        zelvar_pack(),
        answer(said(FIGURE_TEXT, ABSTRACT_ID, FIGURE_QUOTE)),
    )
    verified = await store.stored_claims(ZELVAR.slug, "alum", "VERIFIED")
    hybrid = await store.stored_claims(ZELVAR.slug, "alum", "HYBRID")
    claim_id = expected_claim_id("mordant baths held 8 g/l alum and were heated to 60 °c")
    assert claim_id not in verified.views
    assert claim_id in hybrid.views
