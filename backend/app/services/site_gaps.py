from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User
from app.research.site_gaps import SITE_GAP_ACTION, SITE_GAP_TARGET, SiteGap, SiteGapRow

from . import audit

__all__ = ["GAPS_READ_MAX", "gap_detail", "gap_row", "recent_gaps", "record_gap"]

logger = logging.getLogger(__name__)

GAPS_READ_MAX = 500


def gap_detail(gap: SiteGap, client: str | None) -> dict[str, Any]:
    return {
        "kind": gap.kind,
        "subject": _subject_key(gap),
        "wanted": gap.wanted,
        "tried": gap.tried,
        "evidence": list(gap.evidence),
        "client": client,
    }


async def record_gap(session: AsyncSession, user: User, gap: SiteGap, *, client: str | None) -> None:
    detail = gap_detail(gap, client)
    await audit.record(
        session,
        action=SITE_GAP_ACTION,
        actor=user,
        target_type=SITE_GAP_TARGET if gap.subject is not None else None,
        target_id=detail["subject"],
        detail=detail,
    )
    await session.flush()
    logger.info("site gap filed", extra={"gapKind": gap.kind, "subject": detail["subject"], "client": client})


async def recent_gaps(session: AsyncSession, *, days: int, now: datetime) -> list[SiteGapRow]:
    rows = await session.scalars(
        select(AuditLog)
        .where(AuditLog.action == SITE_GAP_ACTION, AuditLog.createdAt >= now - timedelta(days=days))
        .order_by(AuditLog.createdAt.desc(), AuditLog.id)
        .limit(GAPS_READ_MAX)
    )
    return [gap_row(row.createdAt, dict(row.detail or {})) for row in rows]


def gap_row(filed_at: datetime, detail: dict[str, Any]) -> SiteGapRow:
    return SiteGapRow.model_validate({**detail, "filed_at": filed_at})


def _subject_key(gap: SiteGap) -> str | None:
    return None if gap.subject is None else f"{gap.subject.kind}:{gap.subject.slug}"
