from collections.abc import AsyncIterator
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.craft_monograph import DocumentAsk, served_document
from app.models import Craft, StoredDocumentVersion
from app.research.page_revalidation import PageOwners
from app.services.stored_document_versions import (
    REFRESH_RETRY,
    REMOVED_GRACE,
    drop_expired,
    drop_kept_versions,
    drop_withheld,
)
from app.services.stored_documents import (
    Rebuilt,
    claim_refresh,
    rebuild_document,
    stored_copy,
    superseded_copy,
    utc_now,
)

from .component_lifecycle_seed import NOW, lifecycle_seed
from .page_documents_seed import CRAFT, CRAFT_SLUG, FAMILY_SLUG
from .test_removed_versions_db import page
from .test_stored_documents_db import SECTIONS_VERSION, laid_out
from .testimony_seed import rolled_back_session

pytestmark = pytest.mark.db

SECOND = timedelta(seconds=1)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async for opened in rolled_back_session():
        await lifecycle_seed(opened)
        yield opened


def version_row(
    slug: str, version: int, *, replaced: datetime, removed: datetime | None
) -> StoredDocumentVersion:
    return StoredDocumentVersion(
        subjectKind="craft",
        subjectSlug=slug,
        language="en",
        version=version,
        contentHash=f"{version:064d}",
        document="{}",
        supersededAt=replaced,
        removedAt=removed,
    )


async def versions_of(session: AsyncSession, slug: str) -> list[int]:
    rows = await session.scalars(
        select(StoredDocumentVersion.version)
        .where(StoredDocumentVersion.subjectSlug == slug)
        .order_by(StoredDocumentVersion.version)
    )
    return list(rows.all())


async def test_the_version_a_removal_reached_is_read_by_name_until_the_page_s_refresh_and_then_is_not_found(
    session: AsyncSession,
) -> None:
    subject = await page(session)
    first = await stored_copy(session, subject)
    assert first is not None
    await drop_kept_versions(session, PageOwners(crafts=(CRAFT_SLUG,)), now=NOW)
    await laid_out(session)
    rebuilt_at = utc_now()
    assert await rebuild_document(session, subject, now=rebuilt_at) == Rebuilt.CHANGED
    craft = await session.get(Craft, CRAFT)
    assert craft is not None
    asked = DocumentAsk(language="en", version=SECTIONS_VERSION)
    drawn = await served_document(session, craft, asked)
    assert drawn is not None and drawn.withheld is True
    assert (drawn.text, drawn.version) == (first.text, SECTIONS_VERSION)
    current = await served_document(session, craft, DocumentAsk(language="en"))
    assert current is not None and (current.version, current.withheld) == (SECTIONS_VERSION + 1, False)
    await drop_withheld(session, subject.kind, subject.slug, before=rebuilt_at - SECOND)
    assert await served_document(session, craft, asked) is not None
    await drop_withheld(session, subject.kind, subject.slug, before=rebuilt_at)
    assert await served_document(session, craft, asked) is None
    assert await versions_of(session, CRAFT_SLUG) == []


async def test_a_confirmed_refresh_drops_only_the_withheld_versions_replaced_before_it_was_sent(
    session: AsyncSession,
) -> None:
    session.add_all(
        [
            version_row(CRAFT_SLUG, 1, replaced=NOW - timedelta(days=1), removed=None),
            version_row(CRAFT_SLUG, 2, replaced=NOW, removed=NOW - SECOND),
            version_row(CRAFT_SLUG, 3, replaced=NOW + SECOND, removed=NOW),
            version_row(FAMILY_SLUG, 2, replaced=NOW, removed=NOW - SECOND),
        ]
    )
    await session.flush()
    await drop_withheld(session, "craft", CRAFT_SLUG, before=NOW)
    assert await versions_of(session, CRAFT_SLUG) == [1, 3]
    assert await versions_of(session, FAMILY_SLUG) == [2]


async def test_the_documents_step_drops_withheld_versions_past_their_grace_and_keeps_the_rest(
    session: AsyncSession,
) -> None:
    subject = await page(session)
    session.add_all(
        [
            version_row(CRAFT_SLUG, 1, replaced=NOW - timedelta(days=1), removed=None),
            version_row(CRAFT_SLUG, 2, replaced=NOW - REMOVED_GRACE, removed=NOW - timedelta(hours=1)),
            version_row(
                CRAFT_SLUG, 3, replaced=NOW - REMOVED_GRACE + SECOND, removed=NOW - timedelta(hours=1)
            ),
        ]
    )
    await session.flush()
    assert await superseded_copy(session, subject, 2, now=NOW) is None
    late = await superseded_copy(session, subject, 3, now=NOW)
    assert late is not None and late.withheld is True
    kept = await superseded_copy(session, subject, 1, now=NOW)
    assert kept is not None and kept.withheld is False
    await drop_expired(session, now=NOW)
    assert await versions_of(session, CRAFT_SLUG) == [1, 3]


async def test_a_later_removal_drops_a_withheld_version_with_the_kept_ones(session: AsyncSession) -> None:
    session.add_all(
        [
            version_row(CRAFT_SLUG, 1, replaced=NOW - timedelta(days=1), removed=None),
            version_row(CRAFT_SLUG, 2, replaced=NOW, removed=NOW - SECOND),
        ]
    )
    await session.flush()
    await drop_kept_versions(session, PageOwners(crafts=(CRAFT_SLUG,)), now=NOW)
    assert await versions_of(session, CRAFT_SLUG) == []


async def test_a_page_s_refresh_is_asked_at_most_once_a_retry_and_never_for_a_page_with_no_copy(
    session: AsyncSession,
) -> None:
    subject = await page(session)
    family = await page(session, "family", FAMILY_SLUG)
    assert await claim_refresh(session, family, now=NOW) is False
    assert await stored_copy(session, subject) is not None
    assert await claim_refresh(session, subject, now=NOW) is True
    assert await claim_refresh(session, subject, now=NOW + REFRESH_RETRY - SECOND) is False
    assert await claim_refresh(session, subject, now=NOW + REFRESH_RETRY + SECOND) is True
