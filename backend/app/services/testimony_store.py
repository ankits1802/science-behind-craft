from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, InvalidInput
from app.models import ArtisanContribution, ArtisanConversation, Claim, Craft, Source
from app.research.testimony import CONTRIBUTION_STATUSES, Speaker

from .knowledge_view import source_ref
from .testimony_claims import ARTISAN_ORIGIN, contribution_locator, conversation_speaker

__all__ = [
    "PAGE_SIZE",
    "STALE_DETAIL",
    "ContributionProblems",
    "MoveRefused",
    "OwnContribution",
    "ReviewPage",
    "StaleContribution",
    "TestimonyQuote",
    "UnknownContribution",
    "approved_quote_count",
    "approved_quote_order",
    "approved_quotes",
    "contribution_for_update",
    "conversation_contributions",
    "owned_contribution",
    "page_offset",
    "quote_states",
    "refuse_own",
    "review_page",
    "status_counts",
    "user_contributions",
]

PAGE_SIZE = 25
CURSOR_MAX_OFFSET = 100_000
STALE_DETAIL = "Someone changed this contribution. Reload it."
APPROVED = "APPROVED"


class UnknownContribution(AppError):
    pass


class StaleContribution(AppError):
    pass


class MoveRefused(AppError):
    pass


class OwnContribution(AppError):
    pass


class ContributionProblems(InvalidInput):
    def __init__(self, problems: Sequence[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = list(problems)


@dataclass(frozen=True, kw_only=True)
class ReviewPage:
    counts: dict[str, int]
    total: int
    rows: list[ArtisanContribution]
    next_cursor: str | None


@dataclass(frozen=True, kw_only=True)
class TestimonyQuote:
    item_id: str
    contribution_id: uuid.UUID
    craft_id: uuid.UUID
    discipline: str
    speaker: Speaker
    quote: str
    language: str
    english: str | None
    english_source: str
    source_id: uuid.UUID
    locator: str
    recorded_on: str
    approved_at: datetime
    corroborated_by: tuple[uuid.UUID, ...]
    source: Mapping[str, Any] = field(default_factory=dict)


def page_offset(cursor: str | None) -> int:
    if cursor is None:
        return 0
    if not cursor.isdigit() or int(cursor) > CURSOR_MAX_OFFSET or int(cursor) % PAGE_SIZE:
        raise InvalidInput("Unknown cursor.")
    return int(cursor)


async def contribution_for_update(session: AsyncSession, contribution_id: uuid.UUID) -> ArtisanContribution:
    found = await session.get(ArtisanContribution, contribution_id, with_for_update=True)
    if found is None:
        raise UnknownContribution(f"no contribution {contribution_id}")
    return found


def refuse_own(contribution: ArtisanContribution, reviewer: Any) -> None:
    if contribution.userId == getattr(reviewer, "id", None):
        raise OwnContribution(f"contribution {contribution.id} is the reviewer's own")


async def owned_contribution(
    session: AsyncSession, user_id: uuid.UUID, contribution_id: uuid.UUID, *, lock: bool = False
) -> ArtisanContribution:
    found = await session.get(ArtisanContribution, contribution_id, with_for_update=lock)
    if found is None or found.userId != user_id:
        raise UnknownContribution(f"no contribution {contribution_id} of this account")
    return found


def _filters(
    *, craft_id: uuid.UUID | None, language: str | None, reviewer_id: uuid.UUID | None = None
) -> list[Any]:
    filters: list[Any] = []
    if reviewer_id is not None:
        filters.append(ArtisanContribution.userId != reviewer_id)
    if craft_id is not None:
        filters.append(ArtisanContribution.craftId == craft_id)
    if language is not None:
        filters.append(ArtisanContribution.quoteLanguage == language)
    return filters


async def status_counts(session: AsyncSession, *filters: Any) -> dict[str, int]:
    rows = await session.execute(
        select(ArtisanContribution.status, func.count()).where(*filters).group_by(ArtisanContribution.status)
    )
    found = {str(status): int(count) for status, count in rows.all()}
    return {status.lower(): int(found.get(status, 0)) for status in CONTRIBUTION_STATUSES}


async def review_page(
    session: AsyncSession,
    *,
    status: str,
    craft_id: uuid.UUID | None = None,
    language: str | None = None,
    cursor: str | None = None,
    reviewer_id: uuid.UUID | None = None,
) -> ReviewPage:
    offset = page_offset(cursor)
    filters = _filters(craft_id=craft_id, language=language, reviewer_id=reviewer_id)
    counts = await status_counts(session, *filters)
    order = (ArtisanContribution.createdAt, ArtisanContribution.id)
    rows = list(
        await session.scalars(
            select(ArtisanContribution)
            .where(*filters, ArtisanContribution.status == status)
            .order_by(*order)
            .offset(offset)
            .limit(PAGE_SIZE)
        )
    )
    total = counts[status.lower()]
    following = offset + PAGE_SIZE
    return ReviewPage(
        counts=counts, total=total, rows=rows, next_cursor=str(following) if following < total else None
    )


async def user_contributions(
    session: AsyncSession, user_id: uuid.UUID, *, status: str | None = None
) -> tuple[dict[str, int], list[ArtisanContribution]]:
    owner = ArtisanContribution.userId == user_id
    counts = await status_counts(session, owner)
    query = select(ArtisanContribution).where(owner)
    if status is not None:
        query = query.where(ArtisanContribution.status == status)
    rows = await session.scalars(query.order_by(ArtisanContribution.createdAt.desc(), ArtisanContribution.id))
    return counts, list(rows)


async def conversation_contributions(
    session: AsyncSession, conversation_id: uuid.UUID
) -> list[ArtisanContribution]:
    rows = await session.scalars(
        select(ArtisanContribution)
        .where(ArtisanContribution.conversationId == conversation_id)
        .order_by(ArtisanContribution.ordinal, ArtisanContribution.startMs, ArtisanContribution.id)
    )
    return list(rows)


def _approved_rows(*where: Any) -> Any:
    return (
        select(ArtisanContribution, ArtisanConversation, Craft, Source)
        .join(Claim, Claim.id == ArtisanContribution.claimId)
        .join(ArtisanConversation, ArtisanConversation.id == ArtisanContribution.conversationId)
        .join(Craft, Craft.id == ArtisanContribution.craftId)
        .join(Source, Source.id == ArtisanConversation.sourceId)
        .where(
            Claim.origin == ARTISAN_ORIGIN,
            Claim.status == APPROVED,
            ArtisanContribution.status == APPROVED,
            func.cardinality(ArtisanContribution.screens) == 0,
            ArtisanConversation.deletedAt.is_(None),
            *where,
        )
    )


async def approved_quote_count(session: AsyncSession, craft_id: uuid.UUID) -> int:
    query = _approved_rows(ArtisanContribution.craftId == craft_id).with_only_columns(func.count())
    return int(await session.scalar(query) or 0)


def approved_quote_order(craft_id: uuid.UUID) -> Any:
    return _approved_rows(ArtisanContribution.craftId == craft_id).with_only_columns(
        ArtisanConversation.startedAt.label("moment"),
        ArtisanContribution.approvedAt.label("settled"),
        ArtisanContribution.id.label("item"),
    )


async def approved_quotes(
    session: AsyncSession,
    craft_id: uuid.UUID,
    *,
    limit: int,
    cursor: int = 0,
    disciplines: Iterable[str] | None = None,
) -> list[TestimonyQuote]:
    where = [ArtisanContribution.craftId == craft_id]
    if disciplines is not None:
        where.append(ArtisanContribution.discipline.in_(list(disciplines)))
    query = (
        _approved_rows(*where)
        .order_by(
            ArtisanConversation.startedAt.desc(),
            ArtisanContribution.approvedAt.desc(),
            ArtisanContribution.id,
        )
        .offset(max(cursor, 0))
        .limit(limit)
    )
    rows = (await session.execute(query)).all()
    return [await _quote(session, *row) for row in rows]


async def quote_states(
    session: AsyncSession, contribution_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, TestimonyQuote]:
    wanted = list(dict.fromkeys(contribution_ids))
    if not wanted:
        return {}
    rows = (await session.execute(_approved_rows(ArtisanContribution.id.in_(wanted)))).all()
    return {row[0].id: await _quote(session, *row) for row in rows}


async def _quote(
    session: AsyncSession,
    contribution: ArtisanContribution,
    conversation: ArtisanConversation,
    craft: Craft,
    source: Source,
) -> TestimonyQuote:
    credit = await conversation_speaker(session, contribution.userId, craft)
    return TestimonyQuote(
        item_id=f"kalavigyan:{contribution.id}",
        contribution_id=contribution.id,
        craft_id=craft.id,
        discipline=contribution.discipline,
        speaker=credit,
        quote=contribution.quote or "",
        language=contribution.quoteLanguage,
        english=contribution.english,
        english_source=contribution.englishSource,
        source_id=source.id,
        locator=contribution_locator(contribution),
        recorded_on=conversation.startedAt.strftime("%Y-%m"),
        approved_at=contribution.approvedAt or contribution.updatedAt,
        corroborated_by=tuple(contribution.corroboratingClaimIds or ()),
        source=source_ref(source),
    )
