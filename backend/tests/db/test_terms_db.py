import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import Claim, Craft, Term, TermConcept, TermCraft, TermSummary
from app.research.composition import ComposedSentence, QuotedSpan
from app.research.evidence import EvidenceItem
from app.research.term_marking import TermMarker
from app.services.claim_seed import seed_id
from app.services.term_glossary import glossary_entries, seed_terms
from app.services.term_research import ResearchedSummary
from app.services.term_store import SqlTermStore
from app.services.term_summaries import TermLookup
from app.sources.adapter import build_document

from ..answering.fakes import translation
from ..terms.fakes import CHECKED_AT, FakeResearch, golden_term

pytestmark = pytest.mark.db

KUT_CLAIM = uuid.UUID("c407fde1-3c40-5c81-8a5e-320317aacf9d")
KUT_MATERIAL = seed_id("concept", "ie:ajrakh.material.kut-iron-paste")
PAGE = "https://crafts.example.org/ajrakh/neerani"
TEXT = "Neerani is an emulsion of castor oil, soda ash and camel dung. Cloth is soaked in it at least three times."
SENTENCE = "Neerani is an emulsion of castor oil, soda ash and camel dung."


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


def store_for(session: AsyncSession) -> SqlTermStore:
    def sessions() -> AsyncSession:
        return AsyncSession(bind=session.bind, expire_on_commit=False, autoflush=False)

    return SqlTermStore(sessions)


def lookup(store: SqlTermStore, found: ResearchedSummary | None = None) -> TermLookup:
    return TermLookup(
        store=store, research=FakeResearch(found), translation=translation(), clock=lambda: CHECKED_AT
    )


async def test_the_seeded_glossary_links_kut_to_its_craft_and_material(session: AsyncSession) -> None:
    kut = await session.scalar(select(Term).where(Term.key == "kut"))
    assert kut is not None
    assert (kut.label, kut.meaning) == ("Kut", "iron-water black paste")
    crafts = await session.scalars(
        select(Craft.slug).join(TermCraft, TermCraft.craftId == Craft.id).where(TermCraft.termId == kut.id)
    )
    assert list(crafts) == ["Kutch-Ajrakh"]
    concepts = set(await session.scalars(select(TermConcept.conceptId).where(TermConcept.termId == kut.id)))
    assert KUT_MATERIAL in concepts


async def test_seeding_the_glossary_again_adds_nothing(session: AsyncSession) -> None:
    before = await session.scalar(select(func.count()).select_from(Term))
    again = await seed_terms(session)
    assert again["newLinks"] == 0
    assert await session.scalar(select(func.count()).select_from(Term)) == before == again["terms"]


async def test_kut_is_summarised_from_its_defining_stored_claim(session: AsyncSession) -> None:
    found = await lookup(store_for(session)).summary("kut", "en")
    golden = golden_term()
    assert found.basis == "STORED"
    assert found.summary[0].model_dump(mode="json", by_alias=True) == golden["summary"][0]
    assert found.sources[0].model_dump(mode="json", by_alias=True) == golden["sources"][0]
    row = await session.scalar(
        select(TermSummary).where(TermSummary.language == "en", TermSummary.basis == "STORED")
    )
    assert row is not None and KUT_CLAIM in row.claimIds


async def test_a_cached_summary_resting_on_a_retracted_claim_is_built_again(session: AsyncSession) -> None:
    store = store_for(session)
    term = await store.term("kut")
    assert term is not None
    await lookup(store).summary("kut", "en")
    assert await store.cached(term.id, "en") is not None
    await session.execute(update(Claim).where(Claim.id == KUT_CLAIM).values(status="RETRACTED"))
    assert await store.cached(term.id, "en") is None


async def test_a_researched_summary_is_written_back_as_quoted_claims_of_the_terms_concept(
    session: AsyncSession,
) -> None:
    item = EvidenceItem(
        id=f"searxng:{PAGE}",
        adapter="searxng",
        tier="T4",
        source_type="WEB_PAGE",
        url=PAGE,
        title="Neerani for Ajrakh",
        retrieved_at=datetime(2026, 11, 17, 10, 0, tzinfo=UTC),
        trust="C",
    )
    sentence = ComposedSentence(
        text=SENTENCE, evidence_ids=[item.id], spans=[QuotedSpan(ref=item.id, text=SENTENCE)]
    )
    found = ResearchedSummary("WEB_SEARCH", (build_document(item, TEXT, "FULL_TEXT"),), (sentence,))
    store = store_for(session)
    term = await store.term("neerani")
    assert term is not None
    await session.execute(
        update(Claim)
        .where(Claim.subjectType == "CONCEPT", Claim.subjectId.in_([c.concept_id for c in term.concepts]))
        .values(status="RETRACTED")
    )
    summary = await lookup(store, found).summary("neerani", "en")
    assert (summary.basis, [s.text for s in summary.summary]) == ("WEB_SEARCH", [SENTENCE])
    claim = await session.get(Claim, uuid.UUID(summary.summary[0].citations[0].claim_id))
    assert claim is not None
    assert (claim.evidenceLevel, claim.subjectId) == ("PROVISIONAL", term.concepts[0].concept_id)
    assert [source.url for source in summary.sources] == [PAGE]


async def test_the_glossary_of_a_craft_marks_its_local_names_but_not_its_own_name(
    session: AsyncSession,
) -> None:
    craft_id = await session.scalar(select(Craft.id).where(Craft.slug == "Kutch-Ajrakh"))
    entries = await glossary_entries(session, [craft_id])
    keys = {entry.key for entry in entries}
    assert {"kut", "harde"} <= keys
    assert "kutch-ajrakh" not in keys
    spans = TermMarker(entries).spans("Kut is printed on harde-treated cloth in Kutch Ajrakh.")
    assert [(span.text, span.term_key) for span in spans] == [("Kut", "kut"), ("harde", "harde")]
