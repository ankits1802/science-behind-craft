from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StoredDocument, StoredDocumentVersion
from app.research.page_revalidation import PageOwners

from .open_work_subjects import CATEGORY, WorkSubject

__all__ = [
    "PAGE_LOCK",
    "drop_kept_versions",
    "drop_superseded",
    "keep_superseded",
    "lock_page",
    "page_lock_id",
    "superseded_row",
]

KEPT_COLUMNS = ("contentHash", "document", "supersededAt")
PAGE_LOCK = "stored-document:{space}:{slug}"
CRAFT_SPACE = "craft"


def page_lock_id(kind: str, slug: str) -> ColumnElement[Any]:
    space = CATEGORY if kind == CATEGORY else CRAFT_SPACE
    return func.hashtextextended(PAGE_LOCK.format(space=space, slug=slug), 0)


async def lock_page(session: AsyncSession, kind: str, slug: str) -> None:
    await session.execute(select(func.pg_advisory_xact_lock(page_lock_id(kind, slug))))


async def keep_superseded(session: AsyncSession, row: StoredDocument, *, now: datetime) -> None:
    values = {
        "subjectKind": row.subjectKind,
        "subjectSlug": row.subjectSlug,
        "language": row.language,
        "version": row.version,
        "contentHash": row.contentHash,
        "document": row.document,
        "supersededAt": now,
    }
    statement = insert(StoredDocumentVersion).values(**values)
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[
                StoredDocumentVersion.subjectKind,
                StoredDocumentVersion.subjectSlug,
                StoredDocumentVersion.language,
                StoredDocumentVersion.version,
            ],
            set_={name: statement.excluded[name] for name in KEPT_COLUMNS},
        )
    )


async def superseded_row(
    session: AsyncSession, subject: WorkSubject, version: int, language: str
) -> StoredDocumentVersion | None:
    key = (subject.kind, subject.slug, language, version)
    return await session.get(StoredDocumentVersion, key, populate_existing=True)


async def drop_superseded(session: AsyncSession, subject: WorkSubject) -> None:
    await session.execute(
        delete(StoredDocumentVersion).where(
            StoredDocumentVersion.subjectKind == subject.kind,
            StoredDocumentVersion.subjectSlug == subject.slug,
        )
    )


async def drop_kept_versions(session: AsyncSession, owners: PageOwners, *, now: datetime) -> None:
    if owners.empty:
        return
    for kind, slug in _pages(owners):
        await lock_page(session, kind, slug)
    await session.execute(delete(StoredDocumentVersion).where(_owned(StoredDocumentVersion, owners)))
    await session.execute(
        update(StoredDocument)
        .where(_owned(StoredDocument, owners))
        .values(removedAt=now)
        .execution_options(synchronize_session=False)
    )


def _pages(owners: PageOwners) -> list[tuple[str, str]]:
    crafts = {(CRAFT_SPACE, slug) for slug in owners.crafts}
    return sorted(crafts | {(CATEGORY, slug) for slug in owners.categories})


def _owned(
    table: type[StoredDocument] | type[StoredDocumentVersion], owners: PageOwners
) -> ColumnElement[bool]:
    return or_(
        and_(table.subjectKind != CATEGORY, table.subjectSlug.in_(sorted(owners.crafts))),
        and_(table.subjectKind == CATEGORY, table.subjectSlug.in_(sorted(owners.categories))),
    )
