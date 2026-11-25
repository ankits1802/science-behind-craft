from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, and_, delete, func, or_, select, union, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StoredDocument, StoredDocumentVersion
from app.research.document_parts import compact_json
from app.research.page_revalidation import PageOwners

from .open_work_subjects import CATEGORY, WorkSubject

__all__ = [
    "KEPT_VERSIONS_MAX",
    "PAGE_LOCK",
    "PAGE_REVALIDATE",
    "REMOVAL_LOCK",
    "drop_kept_versions",
    "drop_superseded",
    "keep_superseded",
    "lock_page",
    "page_lock_id",
    "removal_lock_id",
    "superseded_row",
]

KEPT_COLUMNS = ("contentHash", "document", "supersededAt")
PAGE_LOCK = "stored-document:{space}:{slug}"
REMOVAL_LOCK = "stored-document:removals"
CRAFT_SPACE = "craft"
PAGE_REVALIDATE = timedelta(seconds=604_800)
KEPT_VERSIONS_AN_HOUR = 1
KEPT_VERSIONS_MAX = int(PAGE_REVALIDATE / timedelta(hours=1)) * KEPT_VERSIONS_AN_HOUR


def page_lock_id(kind: str, slug: str) -> ColumnElement[Any]:
    space = CATEGORY if kind == CATEGORY else CRAFT_SPACE
    return func.hashtextextended(PAGE_LOCK.format(space=space, slug=slug), 0)


def removal_lock_id() -> ColumnElement[Any]:
    return func.hashtextextended(REMOVAL_LOCK, 0)


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
    await _capped(session, row)


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


async def drop_kept_versions(
    session: AsyncSession, owners: PageOwners, *, now: datetime, marks: Sequence[str] = ()
) -> None:
    if owners.empty:
        return
    await session.execute(select(func.pg_advisory_xact_lock(removal_lock_id())))
    for kind, slug in _pages(owners):
        await lock_page(session, kind, slug)
    reached = await _drawing(session, owners, marks) if marks else owners
    if reached.empty:
        return
    await session.execute(delete(StoredDocumentVersion).where(_owned(StoredDocumentVersion, reached)))
    await session.execute(
        update(StoredDocument)
        .where(_owned(StoredDocument, reached))
        .values(removedAt=now)
        .execution_options(synchronize_session=False)
    )


async def _capped(session: AsyncSession, row: StoredDocument) -> None:
    same = and_(
        StoredDocumentVersion.subjectKind == row.subjectKind,
        StoredDocumentVersion.subjectSlug == row.subjectSlug,
        StoredDocumentVersion.language == row.language,
    )
    newest = (
        select(StoredDocumentVersion.version)
        .where(same)
        .order_by(StoredDocumentVersion.version.desc())
        .limit(KEPT_VERSIONS_MAX)
    )
    await session.execute(
        delete(StoredDocumentVersion).where(same, StoredDocumentVersion.version.not_in(newest))
    )


async def _drawing(session: AsyncSession, owners: PageOwners, marks: Sequence[str]) -> PageOwners:
    copies = [
        select(table.subjectKind, table.subjectSlug).where(_owned(table, owners), _holds(table, marks))
        for table in (StoredDocument, StoredDocumentVersion)
    ]
    found = (await session.execute(union(*copies))).all()
    return PageOwners(
        crafts=tuple(sorted({slug for kind, slug in found if kind != CATEGORY})),
        categories=tuple(sorted({slug for kind, slug in found if kind == CATEGORY})),
    )


def _holds(
    table: type[StoredDocument] | type[StoredDocumentVersion], marks: Sequence[str]
) -> ColumnElement[bool]:
    return or_(*(table.document.contains(compact_json(mark), autoescape=True) for mark in marks))


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
