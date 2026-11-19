from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ExternalFailure
from app.curation.parts import WAYBACK_SNAPSHOT_PATTERN
from app.models import Source, SourceUpkeep

from .upkeep_records import record_archive, record_archive_try

__all__ = [
    "ARCHIVES_PER_NIGHT",
    "ARCHIVE_RETRY_AFTER",
    "ArchiveReport",
    "AtRisk",
    "SourceArchiver",
    "archive_sources",
    "sources_at_risk",
]

logger = logging.getLogger(__name__)

ARCHIVES_PER_NIGHT = 10
ARCHIVE_RETRY_AFTER = timedelta(days=30)
OPEN_SENSITIVITY = "OPEN"
ALIVE = "FETCHED"
HTTPS_PREFIX = "https://"
ARCHIVE_PREFIX = "https://web.archive.org/"
ARCHIVED_KEY = "archivedUrl"
SNAPSHOT = re.compile(WAYBACK_SNAPSHOT_PATTERN)


class SourceArchiver(Protocol):
    async def save(self, url: str) -> str: ...


@dataclass(frozen=True)
class AtRisk:
    source_id: uuid.UUID
    url: str


@dataclass
class ArchiveReport:
    archived: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"archived": len(self.archived), "archiveFailed": len(self.failed)}


async def sources_at_risk(session: AsyncSession, *, now: datetime, limit: int) -> list[AtRisk]:
    statement = (
        select(Source.id, Source.url)
        .join(SourceUpkeep, SourceUpkeep.sourceId == Source.id)
        .where(
            Source.sensitivity == OPEN_SENSITIVITY,
            Source.doi.is_(None),
            Source.url.startswith(HTTPS_PREFIX),
            ~Source.url.startswith(ARCHIVE_PREFIX),
            ~Source.externalIds.has_key(ARCHIVED_KEY),
            SourceUpkeep.outcome == ALIVE,
            SourceUpkeep.archiveUrl.is_(None),
            or_(
                SourceUpkeep.archiveTriedAt.is_(None),
                SourceUpkeep.archiveTriedAt < now - ARCHIVE_RETRY_AFTER,
            ),
        )
        .order_by(SourceUpkeep.checkedAt.desc(), Source.id)
        .limit(limit)
    )
    return [AtRisk(row.id, row.url) for row in (await session.execute(statement)).all()]


async def archive_sources(
    session: AsyncSession, archiver: SourceArchiver, *, now: datetime, limit: int = ARCHIVES_PER_NIGHT
) -> ArchiveReport:
    report = ArchiveReport()
    for source in await sources_at_risk(session, now=now, limit=limit):
        snapshot = await _saved(archiver, source)
        if snapshot is None:
            report.failed.append(str(source.source_id))
            await record_archive_try(session, source.source_id, now=now)
        else:
            report.archived.append(str(source.source_id))
            await record_archive(session, source.source_id, snapshot, now=now)
        await session.commit()
    return report


async def _saved(archiver: SourceArchiver, source: AtRisk) -> str | None:
    try:
        snapshot = await archiver.save(source.url)
    except ExternalFailure as failure:
        logger.warning("source %s could not be archived: %s", source.source_id, failure.kind)
        return None
    if SNAPSHOT.match(snapshot) is None:
        logger.warning("source %s was archived at an address off the snapshot pattern", source.source_id)
        return None
    return snapshot
