from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ExternalFailure
from app.curation.matching import match_key, quote_found
from app.models import ClaimSource, Source, SourceUpkeep
from app.research.fetcher import Fetcher, FetchRefused, FetchRequest

from .upkeep_records import record_fetch

__all__ = [
    "QUOTE_RECHECK_AFTER",
    "QUOTE_SOURCES_PER_NIGHT",
    "CitedQuote",
    "DueSource",
    "QuotesReport",
    "quote_verdicts",
    "recheck_quotes",
    "sources_due",
]

QUOTE_SOURCES_PER_NIGHT = 50
QUOTE_RECHECK_AFTER = timedelta(days=30)
HTTPS_PREFIX = "https://"
PASS = "PASS"
FAIL = "FAIL"
BAD_URL = "BAD_URL"


@dataclass(frozen=True)
class CitedQuote:
    claim_source_id: uuid.UUID
    quote: str


@dataclass(frozen=True)
class DueSource:
    source_id: uuid.UUID
    url: str
    quotes: tuple[CitedQuote, ...]


@dataclass
class QuotesReport:
    sources: list[str] = field(default_factory=list)
    fetched: int = 0
    refused: int = 0
    failed: int = 0
    quotes_passed: int = 0
    quotes_failed: int = 0
    quotes_undecided: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "sourcesChecked": len(self.sources),
            "fetched": self.fetched,
            "refused": self.refused,
            "unreachable": self.failed,
            "quotesPassed": self.quotes_passed,
            "quotesFailed": self.quotes_failed,
            "quotesUndecided": self.quotes_undecided,
        }


def quote_verdicts(text: str, *, truncated: bool, quotes: Sequence[CitedQuote]) -> dict[uuid.UUID, str]:
    key = match_key(text)
    verdicts: dict[uuid.UUID, str] = {}
    for cited in quotes:
        if quote_found(cited.quote, key):
            verdicts[cited.claim_source_id] = PASS
        elif not truncated:
            verdicts[cited.claim_source_id] = FAIL
    return verdicts


async def sources_due(session: AsyncSession, *, now: datetime, limit: int) -> list[DueSource]:
    statement = (
        select(Source.id, Source.url)
        .outerjoin(SourceUpkeep, SourceUpkeep.sourceId == Source.id)
        .where(
            Source.url.startswith(HTTPS_PREFIX),
            exists().where(ClaimSource.sourceId == Source.id),
            or_(SourceUpkeep.checkedAt.is_(None), SourceUpkeep.checkedAt < now - QUOTE_RECHECK_AFTER),
        )
        .order_by(SourceUpkeep.checkedAt.asc().nulls_first(), Source.id)
        .limit(limit)
    )
    rows = (await session.execute(statement)).all()
    quotes = await _quotes_of(session, [row.id for row in rows])
    return [DueSource(row.id, row.url, tuple(quotes.get(row.id, ()))) for row in rows]


async def recheck_quotes(
    session: AsyncSession, fetcher: Fetcher, *, now: datetime, limit: int = QUOTE_SOURCES_PER_NIGHT
) -> QuotesReport:
    report = QuotesReport()
    for due in await sources_due(session, now=now, limit=limit):
        report.sources.append(str(due.source_id))
        await _recheck(session, fetcher, due, (report, now))
        await session.commit()
    return report


async def _recheck(
    session: AsyncSession, fetcher: Fetcher, due: DueSource, run: tuple[QuotesReport, datetime]
) -> None:
    report, now = run
    try:
        page = await fetcher.fetch(FetchRequest(url=due.url))
    except (FetchRefused, ValidationError) as refused:
        report.refused += 1
        reason = refused.reason if isinstance(refused, FetchRefused) else BAD_URL
        await record_fetch(session, due.source_id, outcome="REFUSED", problem=reason, now=now)
        return
    except ExternalFailure as failure:
        report.failed += 1
        problem = f"{failure.kind} {failure.status}" if failure.status else failure.kind
        await record_fetch(session, due.source_id, outcome="FAILED", problem=problem, now=now)
        return
    report.fetched += 1
    verdicts = quote_verdicts(page.text, truncated=page.truncated, quotes=due.quotes)
    await _record_verdicts(session, verdicts, now)
    report.quotes_passed += sum(1 for verdict in verdicts.values() if verdict == PASS)
    report.quotes_failed += sum(1 for verdict in verdicts.values() if verdict == FAIL)
    report.quotes_undecided += len(due.quotes) - len(verdicts)
    await record_fetch(session, due.source_id, outcome="FETCHED", problem=None, now=now)


async def _record_verdicts(session: AsyncSession, verdicts: dict[uuid.UUID, str], now: datetime) -> None:
    for verdict in (PASS, FAIL):
        ids = [claim_source_id for claim_source_id, found in verdicts.items() if found == verdict]
        if ids:
            await session.execute(
                update(ClaimSource).where(ClaimSource.id.in_(ids)).values(quoteCheck=verdict, checkedAt=now)
            )


async def _quotes_of(session: AsyncSession, source_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[CitedQuote]]:
    if not source_ids:
        return {}
    rows = await session.execute(
        select(ClaimSource.id, ClaimSource.sourceId, ClaimSource.quote)
        .where(ClaimSource.sourceId.in_(source_ids), ClaimSource.quote.is_not(None))
        .order_by(ClaimSource.id)
    )
    found: dict[uuid.UUID, list[CitedQuote]] = defaultdict(list)
    for claim_source_id, source_id, quote in rows.all():
        found[source_id].append(CitedQuote(claim_source_id, quote))
    return found
