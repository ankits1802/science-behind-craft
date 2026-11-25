import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.craft_monograph import DocumentAsk, served_document
from app.core.db import get_engine
from app.core.errors import Refused
from app.models import (
    ArticleSection,
    Claim,
    ClaimSource,
    Craft,
    KnowledgePiece,
    KnowledgePieceUnlink,
    StoredDocument,
    StoredDocumentVersion,
)
from app.research.page_revalidation import PageOwners
from app.research.review_queue import FactRetraction, QueueRejection
from app.research.staged_reviews import ConfirmedItem, StagedConfirmation, StagedDecision
from app.research.write_back import WRITE_BACK_ORIGIN
from app.services import stored_documents
from app.services.component_lifecycle import withdraw_registered
from app.services.craft_page_hiding import set_page_piece_hidden
from app.services.open_work_subjects import WorkSubject, subject_by_key
from app.services.review_queue_decisions import ItemRef, reject_item, retract_fact
from app.services.staged_review_confirm import confirm_batch
from app.services.staged_reviews import stage_decisions
from app.services.stored_document_stamp import document_stamp
from app.services.stored_document_versions import drop_kept_versions, page_lock_id
from app.services.stored_documents import Rebuilt, rebuild_document, stored_copy, stored_row, superseded_copy

from .component_lifecycle_seed import ADMIN, NOW, OWN, PROPOSER, STRANGER, lifecycle_seed, person
from .page_documents_seed import (
    ALUM,
    BARE,
    CATEGORY_SLUG,
    CONCEPT_PLAYER,
    CRAFT,
    CRAFT_PLAYER,
    CRAFT_SLUG,
    FAMILY_SLUG,
    OTHER_CRAFTS_PLAYER,
    PAPER,
)
from .test_staged_reviews_db import caller_of
from .test_stored_documents_db import SECTIONS_VERSION, laid_out
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

WHY = "It names the mordant of another craft on this page."
LATER = NOW + timedelta(hours=1)
SHOWN_FACT = uuid.UUID("9e1f0000-0000-4000-8000-0000000000a1")
WAITING_FACT = uuid.UUID("9e1f0000-0000-4000-8000-0000000000a2")
SHOWN_TEXT = "The printers rinse the alum paste out in the river at dawn."


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await lifecycle_seed(opened)
        yield opened


async def page(session: AsyncSession, kind: str = "craft", slug: str = CRAFT_SLUG) -> WorkSubject:
    return await subject_by_key(session, kind, slug)


async def kept_slugs(session: AsyncSession) -> list[str]:
    rows = await session.scalars(
        select(StoredDocumentVersion.subjectSlug).where(
            StoredDocumentVersion.subjectSlug.in_([CRAFT_SLUG, FAMILY_SLUG, CATEGORY_SLUG])
        )
    )
    return sorted(rows.all())


async def with_a_kept_version(session: AsyncSession, subject: WorkSubject) -> str:
    first = await stored_copy(session, subject)
    assert first is not None and first.version == SECTIONS_VERSION
    await laid_out(session)
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.CHANGED
    assert await superseded_copy(session, subject, SECTIONS_VERSION) is not None
    return first.text


async def piece_id(session: AsyncSession, label: str) -> uuid.UUID:
    found = await session.scalar(select(KnowledgePiece.id).where(KnowledgePiece.label == label))
    assert found is not None
    return found


async def free_elsewhere(*pages: tuple[str, str]) -> list[bool]:
    async with get_engine().connect() as other:
        taken = [
            bool(await other.scalar(select(func.pg_try_advisory_xact_lock(page_lock_id(kind, slug)))))
            for kind, slug in pages
        ]
        await other.rollback()
    return taken


def one_page_removal(piece: uuid.UUID) -> StagedDecision:
    return StagedDecision.model_validate(
        {"kind": "COMPONENTS", "id": piece, "action": "remove", "reason": WHY, "craft": CRAFT_SLUG}
    )


async def test_a_confirmed_one_page_removal_leaves_no_version_that_draws_it_and_the_rebuild_lacks_it(
    session: AsyncSession,
) -> None:
    subject = await page(session)
    first = await with_a_kept_version(session, subject)
    assert OWN in first
    admin = await person(session, ADMIN)
    staged = await stage_decisions(
        session, [one_page_removal(await piece_id(session, OWN))], await caller_of(session, admin), now=NOW
    )
    assert staged.batch is not None and await kept_slugs(session) == [CRAFT_SLUG]
    chosen = [ConfirmedItem(id=staged.items[0].id, action="remove", reason=WHY, craft=CRAFT_SLUG)]
    await confirm_batch(session, staged.batch.id, StagedConfirmation(items=chosen), admin, now=NOW)
    assert await kept_slugs(session) == []
    craft = await session.get(Craft, CRAFT)
    assert craft is not None
    asked = DocumentAsk(language="en", version=SECTIONS_VERSION)
    assert await served_document(session, craft, asked) is None
    stale = await stored_copy(session, subject)
    assert stale is not None and stale.current is False and OWN in stale.text
    assert await rebuild_document(session, subject, now=LATER) == Rebuilt.CHANGED
    after = await stored_copy(session, subject)
    assert after is not None and (after.current, after.version) == (True, SECTIONS_VERSION + 2)
    assert OWN not in after.text
    assert await superseded_copy(session, subject, SECTIONS_VERSION + 1) is None


async def test_a_one_page_unlink_moves_the_stamp_of_the_page_it_names_and_of_no_other(
    session: AsyncSession,
) -> None:
    pages = [await page(session), await page(session, "family", FAMILY_SLUG)]
    pages.append(await page(session, "category", CATEGORY_SLUG))
    before = [await document_stamp(session, subject) for subject in pages]
    session.add(KnowledgePieceUnlink(pieceId=await piece_id(session, OWN), craftId=CRAFT))
    await session.flush()
    moved = [await document_stamp(session, subject) for subject in pages]
    assert [old != new for old, new in zip(before, moved, strict=True)] == [True, False, False]
    session.add(KnowledgePieceUnlink(pieceId=await piece_id(session, CONCEPT_PLAYER), categoryId=pages[2].id))
    await session.flush()
    again = [await document_stamp(session, subject) for subject in pages]
    assert [old != new for old, new in zip(moved, again, strict=True)] == [False, False, True]


def stored_rows(kind: str, slug: str) -> list[StoredDocument | StoredDocumentVersion]:
    held = StoredDocument(
        subjectKind=kind,
        subjectSlug=slug,
        language="en",
        stamp="0" * 64,
        version=2,
        contentHash="0" * 64,
        document="{}",
        builtAt=NOW,
    )
    kept = [
        StoredDocumentVersion(
            subjectKind=kind,
            subjectSlug=slug,
            language=language,
            version=1,
            contentHash="1" * 64,
            document="{}",
            supersededAt=NOW,
        )
        for language in ("en", "hi")
    ]
    return [held, *kept]


async def removal_marks(session: AsyncSession) -> dict[str, Any]:
    rows = await session.execute(
        select(StoredDocument.subjectSlug, StoredDocument.removedAt).where(
            StoredDocument.subjectSlug.in_([CRAFT_SLUG, FAMILY_SLUG, CATEGORY_SLUG])
        )
    )
    return dict(rows.all())


async def test_a_removal_drops_the_kept_versions_of_the_pages_it_reaches_and_waits_for_their_rebuilds(
    session: AsyncSession,
) -> None:
    for kind, slug in (("craft", CRAFT_SLUG), ("family", FAMILY_SLUG), ("category", CATEGORY_SLUG)):
        session.add_all(stored_rows(kind, slug))
    await session.flush()
    await drop_kept_versions(session, PageOwners(), now=NOW)
    assert len(await kept_slugs(session)) == 6
    await drop_kept_versions(session, PageOwners(crafts=(CRAFT_SLUG,)), now=NOW)
    assert await kept_slugs(session) == [CATEGORY_SLUG, CATEGORY_SLUG, FAMILY_SLUG, FAMILY_SLUG]
    assert await removal_marks(session) == {CRAFT_SLUG: NOW, FAMILY_SLUG: None, CATEGORY_SLUG: None}
    assert await free_elsewhere(("family", CRAFT_SLUG), ("category", CATEGORY_SLUG)) == [False, True]
    await drop_kept_versions(session, PageOwners(crafts=(FAMILY_SLUG,), categories=(CATEGORY_SLUG,)), now=NOW)
    assert await kept_slugs(session) == []
    assert await removal_marks(session) == {CRAFT_SLUG: NOW, FAMILY_SLUG: NOW, CATEGORY_SLUG: NOW}


async def test_the_copy_a_removal_reached_is_not_kept_but_the_change_after_it_is(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = await page(session)
    assert await stored_copy(session, subject) is not None
    await drop_kept_versions(session, PageOwners(crafts=(CRAFT_SLUG,)), now=NOW)
    await laid_out(session)
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.CHANGED
    assert await superseded_copy(session, subject, SECTIONS_VERSION) is None
    row = await stored_row(session, subject)
    assert row is not None and row.removedAt is None
    built = stored_documents.generated_document_of

    async def retitled(opened: AsyncSession, asked: WorkSubject) -> Any:
        document = await built(opened, asked)
        return None if document is None else document.model_copy(update={"title": "A later title"})

    monkeypatch.setattr(stored_documents, "generated_document_of", retitled)
    assert await rebuild_document(session, subject, now=LATER) == Rebuilt.CHANGED
    assert await superseded_copy(session, subject, SECTIONS_VERSION + 1) is not None


async def test_a_rebuild_that_finds_a_reached_page_unchanged_clears_its_mark(session: AsyncSession) -> None:
    subject = await page(session)
    first = await stored_copy(session, subject)
    assert first is not None
    await drop_kept_versions(session, PageOwners(crafts=(CRAFT_SLUG,)), now=NOW)
    assert await rebuild_document(session, subject, now=NOW) == Rebuilt.UNCHANGED
    row = await stored_row(session, subject)
    assert row is not None and row.removedAt is None
    await laid_out(session)
    assert await rebuild_document(session, subject, now=LATER) == Rebuilt.CHANGED
    kept = await superseded_copy(session, subject, SECTIONS_VERSION)
    assert kept is not None and kept.text == first.text


async def facts_from_research(session: AsyncSession) -> None:
    for claim_id, status, text in (
        (SHOWN_FACT, "APPROVED", SHOWN_TEXT),
        (WAITING_FACT, "DRAFT", "Alum waits."),
    ):
        session.add(
            Claim(
                id=claim_id,
                subjectType="CONCEPT",
                subjectId=ALUM,
                predicate="states",
                text=text,
                evidenceLevel="PROVISIONAL",
                origin=WRITE_BACK_ORIGIN,
                status=status,
                field="CHEMISTRY",
            )
        )
    await session.flush()
    for claim_id in (SHOWN_FACT, WAITING_FACT):
        session.add(
            ClaimSource(claimId=claim_id, sourceId=PAPER, quote="rinse", locator="p. 7", quoteCheck="PASS")
        )
    section = await session.scalar(
        select(ArticleSection).where(ArticleSection.craftId == CRAFT, ArticleSection.field == "GEOGRAPHY")
    )
    assert section is not None
    section.sentences = [{"text": SHOWN_TEXT, "claimIds": [str(SHOWN_FACT)]}]
    await session.flush()


async def test_a_retracted_fact_leaves_every_kept_version_and_a_waiting_one_rejected_leaves_them(
    session: AsyncSession,
) -> None:
    await facts_from_research(session)
    subject = await page(session)
    assert str(SHOWN_FACT) in await with_a_kept_version(session, subject)
    admin = await person(session, ADMIN)
    rejection = QueueRejection(reason="It restates a fact the page already holds.")
    await reject_item(session, ItemRef("FACTS", WAITING_FACT), admin, rejection, now=NOW)
    assert await kept_slugs(session) == [CRAFT_SLUG]
    await retract_fact(
        session, SHOWN_FACT, admin, FactRetraction(reason="Its quote names another river."), now=NOW
    )
    assert await kept_slugs(session) == []
    assert await rebuild_document(session, subject, now=LATER) == Rebuilt.CHANGED
    after = await stored_copy(session, subject)
    assert after is not None and str(SHOWN_FACT) not in after.text
    assert await superseded_copy(session, subject, SECTIONS_VERSION + 1) is None


async def test_a_proposer_s_withdrawal_drops_the_kept_versions_and_a_stranger_s_refusal_leaves_them(
    session: AsyncSession,
) -> None:
    await with_a_kept_version(session, await page(session))
    with pytest.raises(Refused):
        await withdraw_registered(session, await person(session, STRANGER), OWN, reason=None, now=NOW)
    assert await kept_slugs(session) == [CRAFT_SLUG]
    await withdraw_registered(session, await person(session, PROPOSER), OWN, reason=None, now=NOW)
    assert await kept_slugs(session) == []


async def test_a_piece_hidden_from_its_craft_drops_that_page_s_kept_versions_and_another_craft_s_does_not(
    session: AsyncSession,
) -> None:
    first = await with_a_kept_version(session, await page(session))
    admin = await person(session, ADMIN)
    bare, craft = await session.get(Craft, BARE), await session.get(Craft, CRAFT)
    assert bare is not None and craft is not None
    other = await piece_id(session, OTHER_CRAFTS_PLAYER)
    assert await set_page_piece_hidden(session, bare, other, hidden=True, user=admin, now=NOW) is True
    assert await kept_slugs(session) == [CRAFT_SLUG]
    assert f'"{CRAFT_PLAYER}"' not in first
    undrawn = await piece_id(session, CRAFT_PLAYER)
    assert await set_page_piece_hidden(session, craft, undrawn, hidden=True, user=admin, now=NOW) is True
    assert await kept_slugs(session) == [CRAFT_SLUG]
    assert f'"{OWN}"' in first
    own = await piece_id(session, OWN)
    assert await set_page_piece_hidden(session, craft, own, hidden=True, user=admin, now=NOW) is True
    assert await kept_slugs(session) == []
