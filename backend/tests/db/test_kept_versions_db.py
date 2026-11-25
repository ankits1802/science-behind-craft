import asyncio
import json
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine
from app.models import StoredDocument, StoredDocumentVersion
from app.research.page_revalidation import PageOwners
from app.research.review_queue import FactRetraction
from app.research.staged_reviews import ConfirmedItem, StagedConfirmation
from app.services import stored_document_versions
from app.services.component_lifecycle import withdraw_registered
from app.services.page_revalidation import claim_owners
from app.services.review_queue_decisions import retract_fact
from app.services.staged_review_confirm import confirm_batch
from app.services.staged_reviews import stage_decisions
from app.services.stored_document_versions import drop_kept_versions, keep_superseded

from .component_lifecycle_seed import ADMIN, NOW, OWN, PROPOSER, lifecycle_seed, person
from .page_documents_seed import CATEGORY_SLUG, CRAFT_SLUG, FAMILY_SLUG
from .test_removed_versions_db import (
    SHOWN_FACT,
    WHY,
    facts_from_research,
    free_elsewhere,
    kept_slugs,
    one_page_removal,
    page,
    piece_id,
    removal_marks,
    with_a_kept_version,
)
from .test_staged_reviews_db import caller_of
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

LEFT = "Kept-Versions-Test-Left"
RIGHT = "Kept-Versions-Test-Right"
WAIT_SECONDS = 20
WAITING = text("SELECT count(*) FROM pg_locks WHERE pid = :pid AND locktype = 'advisory' AND NOT granted")


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await lifecycle_seed(opened)
        yield opened


def current(
    kind: str, slug: str, *, version: int, language: str = "en", drawn: object = None
) -> StoredDocument:
    return StoredDocument(
        subjectKind=kind,
        subjectSlug=slug,
        language=language,
        stamp="0" * 64,
        version=version,
        contentHash=f"{version:064d}",
        document=json.dumps({"version": version} if drawn is None else drawn),
        builtAt=NOW,
    )


def copies(kind: str, slug: str, drawn: object) -> list[StoredDocument | StoredDocumentVersion]:
    document = json.dumps(drawn)
    held = current(kind, slug, version=2, drawn=drawn)
    kept = StoredDocumentVersion(
        subjectKind=kind,
        subjectSlug=slug,
        language="en",
        version=1,
        contentHash="1" * 64,
        document=document,
        supersededAt=NOW,
    )
    return [held, kept]


async def test_a_retracted_fact_clears_the_pages_whose_copies_draw_it_and_leaves_those_that_never_did(
    session: AsyncSession,
) -> None:
    await facts_from_research(session)
    assert str(SHOWN_FACT) in await with_a_kept_version(session, await page(session))
    owners = await claim_owners(session, [SHOWN_FACT])
    assert (FAMILY_SLUG in owners.crafts, owners.categories) == (True, (CATEGORY_SLUG,))
    session.add_all(copies("family", FAMILY_SLUG, {"units": {"u1": {"claimIds": [str(SHOWN_FACT)]}}}))
    session.add_all(copies("category", CATEGORY_SLUG, {"units": {"u1": {"claimIds": []}}}))
    await session.flush()
    retraction = FactRetraction(reason="Its quote names another river.")
    await retract_fact(session, SHOWN_FACT, await person(session, ADMIN), retraction, now=NOW)
    assert await kept_slugs(session) == [CATEGORY_SLUG]
    assert await removal_marks(session) == {CRAFT_SLUG: NOW, FAMILY_SLUG: NOW, CATEGORY_SLUG: None}


async def test_a_withdrawn_component_clears_the_pages_that_place_it_and_leaves_a_label_it_only_begins(
    session: AsyncSession,
) -> None:
    assert f'"{OWN}"' in await with_a_kept_version(session, await page(session))
    session.add_all(copies("family", FAMILY_SLUG, {"components": [{"label": OWN}]}))
    session.add_all(copies("category", CATEGORY_SLUG, {"components": [{"label": f"{OWN}-later"}]}))
    await session.flush()
    retired = await withdraw_registered(session, await person(session, PROPOSER), OWN, reason=None, now=NOW)
    assert FAMILY_SLUG in retired.owners.crafts and CATEGORY_SLUG in retired.owners.categories
    assert await kept_slugs(session) == [CATEGORY_SLUG]
    assert await removal_marks(session) == {CRAFT_SLUG: NOW, FAMILY_SLUG: NOW, CATEGORY_SLUG: None}


async def test_a_one_page_removal_clears_only_its_page_though_the_family_places_the_component_too(
    session: AsyncSession,
) -> None:
    await with_a_kept_version(session, await page(session))
    session.add_all(copies("family", FAMILY_SLUG, {"components": [{"label": OWN}]}))
    await session.flush()
    admin = await person(session, ADMIN)
    removal = one_page_removal(await piece_id(session, OWN))
    staged = await stage_decisions(session, [removal], await caller_of(session, admin), now=NOW)
    assert staged.batch is not None
    chosen = [ConfirmedItem(id=staged.items[0].id, action="remove", reason=WHY, craft=CRAFT_SLUG)]
    confirmed = await confirm_batch(
        session, staged.batch.id, StagedConfirmation(items=chosen), admin, now=NOW
    )
    assert FAMILY_SLUG in confirmed.owners.crafts
    assert await kept_slugs(session) == [FAMILY_SLUG]
    assert await removal_marks(session) == {CRAFT_SLUG: NOW, FAMILY_SLUG: None}


async def test_a_removal_leaves_the_pages_whose_copies_lack_its_mark_and_one_naming_none_clears_them_all(
    session: AsyncSession,
) -> None:
    session.add_all(copies("family", FAMILY_SLUG, {"components": []}))
    session.add_all(copies("category", CATEGORY_SLUG, {"components": []}))
    await session.flush()
    owners = PageOwners(crafts=(FAMILY_SLUG,), categories=(CATEGORY_SLUG,))
    await drop_kept_versions(session, owners, now=NOW, marks=(OWN,))
    assert await kept_slugs(session) == [CATEGORY_SLUG, FAMILY_SLUG]
    await drop_kept_versions(session, owners, now=NOW)
    assert await kept_slugs(session) == []
    assert await removal_marks(session) == {FAMILY_SLUG: NOW, CATEGORY_SLUG: NOW}


async def test_kept_versions_are_capped_per_page_and_language_keeping_the_newest(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stored_document_versions, "KEPT_VERSIONS_MAX", 2)
    await keep_superseded(session, current("craft", CRAFT_SLUG, version=1, language="hi"), now=NOW)
    await keep_superseded(session, current("family", FAMILY_SLUG, version=1), now=NOW)
    for version in (1, 2, 3):
        await keep_superseded(session, current("craft", CRAFT_SLUG, version=version), now=NOW)
    rows = await session.execute(
        select(
            StoredDocumentVersion.subjectSlug, StoredDocumentVersion.language, StoredDocumentVersion.version
        )
        .where(StoredDocumentVersion.subjectSlug.in_([CRAFT_SLUG, FAMILY_SLUG]))
        .order_by(
            StoredDocumentVersion.subjectSlug, StoredDocumentVersion.language, StoredDocumentVersion.version
        )
    )
    assert [tuple(row) for row in rows.all()] == [
        (CRAFT_SLUG, "en", 2),
        (CRAFT_SLUG, "en", 3),
        (CRAFT_SLUG, "hi", 1),
        (FAMILY_SLUG, "en", 1),
    ]


async def crossed(session: AsyncSession, *owners: PageOwners) -> None:
    for named in owners:
        await drop_kept_versions(session, named, now=NOW)


async def waits(session: AsyncSession, pid: int) -> None:
    async with asyncio.timeout(WAIT_SECONDS):
        while not await session.scalar(WAITING, {"pid": pid}):
            await asyncio.sleep(0.05)


async def test_two_removals_naming_the_same_pages_in_opposite_orders_wait_in_turn_and_never_deadlock() -> (
    None
):
    left, right = PageOwners(crafts=(LEFT,)), PageOwners(categories=(RIGHT,))
    engine = get_engine()
    async with engine.connect() as one, engine.connect() as two:
        first, second = AsyncSession(bind=one), AsyncSession(bind=two)
        for opened in (first, second):
            await opened.execute(text(f"SET LOCAL lock_timeout = '{WAIT_SECONDS}s'"))
        pid = await second.scalar(select(func.pg_backend_pid()))
        assert pid is not None
        await drop_kept_versions(first, left, now=NOW)
        crossing = asyncio.create_task(crossed(second, right, left))
        await waits(first, int(pid))
        assert await free_elsewhere(("category", RIGHT)) == [True]
        await drop_kept_versions(first, right, now=NOW)
        assert await free_elsewhere(("craft", LEFT), ("category", RIGHT)) == [False, False]
        await first.rollback()
        await asyncio.wait_for(crossing, WAIT_SECONDS)
        await second.rollback()
        await first.close()
        await second.close()
