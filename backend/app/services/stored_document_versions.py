from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StoredDocument, StoredDocumentVersion

from .open_work_subjects import WorkSubject

__all__ = ["drop_superseded", "keep_superseded", "superseded_row"]

KEPT_COLUMNS = ("contentHash", "document", "supersededAt")


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
