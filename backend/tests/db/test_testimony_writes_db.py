from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ArtisanContribution,
    ArtisanConversation,
    ArtisanConversationAudio,
    AuditLog,
    Chunk,
    Claim,
    ClaimSource,
    Concept,
    ReviewEvent,
    Source,
)
from app.retrieval.statements import claim_conditions
from app.services import knowledge_view, testimony_writes
from app.services.artisan_voice_builder import voice_quote_payload
from app.services.testimony_claims import ERASED_STATUS, ERASED_TEXT
from app.services.testimony_readback import refreshed_document
from app.services.testimony_store import approved_quotes, quote_states
from app.services.testimony_writes import ContributionEdit

from .testimony_seed import TURN_TEXT, RecordedObjects, Seeded, rolled_back_session, seed

pytestmark = pytest.mark.db

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        yield opened


async def approved(session: AsyncSession, seeded: Seeded) -> ArtisanContribution:
    return await testimony_writes.approve(
        session,
        seeded.contribution.id,
        seeded.reviewer,
        version=seeded.contribution.version,
        english_checked=True,
        corroborating_ids=[seeded.fact_claim],
        now=NOW,
    )


async def count(session: AsyncSession, *where: object) -> int:
    return int(await session.scalar(select(func.count()).where(*where)) or 0)


async def erased(session: AsyncSession, claim_id: object) -> tuple[object, ...]:
    found = select(Claim.text, Claim.status, Claim.createdById).where(Claim.id == claim_id)
    return tuple((await session.execute(found)).one())


async def test_approval_writes_one_testimony_source(session: AsyncSession) -> None:
    seeded = await seed(session)
    await approved(session, seeded)
    await session.flush()
    source = await session.get(Source, seeded.conversation.sourceId)
    assert source is not None
    assert (source.kind, source.origin, source.sensitivity, source.storage) == (
        "FIELD_TESTIMONY",
        "CONTRIBUTION",
        "ATTRIBUTE_REQUIRED",
        "EXCERPT",
    )
    assert source.title == "Artisan conversation, Testimony Print, 18 November 2026"
    assert (source.publisher, source.reliability, source.url, source.year) == ("KalaVigyan", "C", None, 2026)
    assert source.attribution == "An artisan of Testimony Print, Testimony District, Testimony State"
    assert source.authors == []
    assert source.externalIds == {"kalavigyan": {"conversationId": str(seeded.conversation.id)}}


async def test_approval_writes_the_claim_its_citation_and_the_records(session: AsyncSession) -> None:
    seeded = await seed(session)
    item = await approved(session, seeded)
    await session.flush()
    claim = await session.get(Claim, item.claimId)
    assert claim is not None
    assert (claim.origin, claim.evidenceLevel, claim.sensitivity, claim.status) == (
        "ARTISAN",
        "PROVISIONAL",
        "ATTRIBUTE_REQUIRED",
        "APPROVED",
    )
    assert (claim.field, claim.fields) == ("PROCESS", [])
    assert (claim.predicate, claim.createdById, claim.createdByKind) == (
        "artisan_testimony",
        seeded.artisan.id,
        "USER",
    )
    concept = await session.get(Concept, claim.subjectId)
    assert concept is not None and (concept.sensitivity, concept.originRef) == (
        "ATTRIBUTE_REQUIRED",
        "artisan-testimony",
    )
    cite = await session.scalar(select(ClaimSource).where(ClaimSource.claimId == claim.id))
    assert cite is not None
    assert (cite.quote, cite.locator, cite.quoteCheck, cite.relation, cite.foundBy) == (
        seeded.contribution.quote,
        "1:05–1:12",
        "PASS",
        "DIRECT",
        "artisan_conversation",
    )
    assert await count(session, ReviewEvent.claimId == claim.id, ReviewEvent.toStatus == "APPROVED") == 1
    assert await count(session, Chunk.sourceId == seeded.conversation.sourceId) == 0
    audit = await session.scalar(select(AuditLog).where(AuditLog.targetId == str(item.id)))
    assert audit is not None and audit.action == "testimony.approved"
    assert seeded.contribution.quote not in str(audit.detail)
    assert (item.status, item.englishSource, item.version) == ("APPROVED", "REVIEWED", 2)
    assert item.corroboratingClaimIds == [seeded.fact_claim]


async def test_testimony_is_absent_from_every_fact_reader(session: AsyncSession) -> None:
    seeded = await seed(session)
    item = await approved(session, seeded)
    await session.flush()
    for mode in ("VERIFIED", "HYBRID", "DEEP"):
        views, _sources = await knowledge_view.claims_for(session, seeded.craft, mode=mode)
        assert item.claimId not in {view.id for view in views}, mode
        scoped = claim_conditions(knowledge_view.craft_scope_of(seeded.craft), mode=mode)
        assert await count(session, Claim.id == item.claimId, *scoped) == 0, mode
    views_by_id, _ = await knowledge_view.claims_by_id(session, [item.claimId])
    assert views_by_id == {}
    quotes = await approved_quotes(session, seeded.craft.id, limit=5)
    assert [quote.contribution_id for quote in quotes] == [item.id]


async def test_withdrawal_erases_the_claim_its_source_and_the_text(session: AsyncSession) -> None:
    seeded = await seed(session)
    item = await approved(session, seeded)
    await session.flush()
    (quote,) = await approved_quotes(session, seeded.craft.id, limit=5)
    stored = {
        "sections": [
            {
                "blocks": [
                    {"kind": "artisan_voice", "quotes": [voice_quote_payload(quote, {})], "removed": 0},
                ]
            }
        ],
        "sources": [{"id": str(quote.source_id)}],
    }
    claim_id, source_id = item.claimId, seeded.conversation.sourceId
    objects = RecordedObjects()
    await testimony_writes.withdraw(session, objects, seeded.artisan, item.id, now=NOW + timedelta(hours=1))
    await session.flush()
    assert await erased(session, claim_id) == (ERASED_TEXT, ERASED_STATUS, None)
    assert await count(session, ClaimSource.claimId == claim_id) == 0
    assert await count(session, ReviewEvent.claimId == claim_id, ReviewEvent.toStatus == "APPROVED") == 1
    assert await count(session, ReviewEvent.claimId == claim_id, ReviewEvent.toStatus == ERASED_STATUS) == 1
    assert await session.get(Source, source_id) is None
    assert (item.status, item.quote, item.english, item.claimText, item.claimId) == (
        "WITHDRAWN",
        None,
        None,
        None,
        None,
    )
    assert await quote_states(session, [item.id]) == {}
    shown = refreshed_document(stored, {})
    assert shown["sections"][0]["blocks"][0] == {"kind": "artisan_voice", "quotes": [], "removed": 1}
    assert shown["sources"] == []
    conversation = await session.get(ArtisanConversation, seeded.conversation.id)
    assert conversation is not None and conversation.transcriptEnc is None
    assert len(objects.deleted) == 1
    assert await count(session, ArtisanConversationAudio.conversationId == seeded.conversation.id) == 0


async def test_unshowing_retracts_and_thirty_days_later_the_text_and_claim_go(session: AsyncSession) -> None:
    seeded = await seed(session)
    item = await approved(session, seeded)
    rejected = await testimony_writes.reject(
        session, item.id, seeded.reviewer, version=item.version, reason="PERSONAL_DETAILS", note=None, now=NOW
    )
    await session.flush()
    claim = await session.get(Claim, rejected.claimId)
    assert claim is not None and claim.status == "RETRACTED"
    assert await approved_quotes(session, seeded.craft.id, limit=5) == []
    assert await testimony_writes.clear_expired_rejections(session, now=NOW + timedelta(days=29)) == 0
    assert await testimony_writes.clear_expired_rejections(session, now=NOW + timedelta(days=31)) == 1
    await session.flush()
    assert (rejected.quote, rejected.claimId, rejected.status) == (None, None, "REJECTED")
    assert rejected.textsClearedAt is not None
    assert await erased(session, claim.id) == (ERASED_TEXT, ERASED_STATUS, None)
    assert await count(session, ClaimSource.claimId == claim.id) == 0


async def test_editing_an_approved_contribution_supersedes_its_claim(session: AsyncSession) -> None:
    seeded = await seed(session)
    item = await approved(session, seeded)
    old_claim = item.claimId
    change = ContributionEdit(
        version=item.version, claim_text="The printed cloth is washed in running water."
    )
    edited = await testimony_writes.edit(
        session, item.id, seeded.reviewer, change=change, turn_text=TURN_TEXT, now=NOW
    )
    await session.flush()
    old = await session.get(Claim, old_claim)
    new = await session.get(Claim, edited.claimId)
    assert old is not None and new is not None
    assert (old.status, new.status, new.supersedesId) == ("SUPERSEDED", "APPROVED", old.id)
    assert new.text == "The printed cloth is washed in running water."


async def test_deleting_a_conversation_withdraws_everything_and_purges_at_once(session: AsyncSession) -> None:
    seeded = await seed(session)
    await approved(session, seeded)
    objects = RecordedObjects()
    withdrawn = await testimony_writes.delete_conversation(
        session, objects, seeded.artisan, seeded.conversation.id, now=NOW
    )
    await session.flush()
    conversation = await session.get(ArtisanConversation, seeded.conversation.id)
    assert withdrawn == 1 and conversation is not None
    assert conversation.deletedAt == NOW and conversation.transcriptEnc is None
    assert len(objects.deleted) == 1
    assert await count(session, Claim.origin == "ARTISAN", Claim.createdById == seeded.artisan.id) == 0
    result = await testimony_writes.withdraw_everything(session, None, seeded.artisan, now=NOW)
    assert (result.withdrawn_contributions, result.deleted_conversations) == (0, 0)


async def test_a_held_back_name_is_screened_on_edit_and_blocks_approval(session: AsyncSession) -> None:
    seeded = await seed(session, credit="FIRST_NAME")
    change = ContributionEdit(
        version=seeded.contribution.version, english="Khatri and I wash the cloth after the alum"
    )
    edited = await testimony_writes.edit(
        session, seeded.contribution.id, seeded.reviewer, change=change, turn_text=TURN_TEXT, now=NOW
    )
    assert (edited.screens, edited.englishSource) == (["NAME_HELD_BACK"], "REVIEWED")
    with pytest.raises(testimony_writes.ContributionProblems):
        await testimony_writes.approve(
            session,
            edited.id,
            seeded.reviewer,
            version=edited.version,
            english_checked=False,
            corroborating_ids=[],
            now=NOW,
        )
