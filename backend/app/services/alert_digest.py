from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import INDIA_TZ
from app.models import AccessRoster, AlertDigestSend, User, UserPreference
from app.research.alerts import ALERTS_SCHEMA_VERSION, DIGEST_ITEMS_MAX, AnswerImproved, WeeklyDigest
from app.research.sections import DISCIPLINE_TITLES

from .access_roster import ACTIVE
from .mailer import Mail
from .notifications import unread_improvements

__all__ = [
    "DIGEST_SUBJECT",
    "DIGEST_WINDOW",
    "DigestReport",
    "digest_mail",
    "explainer_url",
    "send_alert_digests",
    "week_of",
    "weekly_digest",
]

logger = logging.getLogger(__name__)

DIGEST_SUBJECT = "Your saved KalaVigyan explainers got better"
DIGEST_WINDOW = timedelta(days=7)
SETTINGS_PATH = "/settings"
EXPLAINER_PATH = "/ask?explainer="

Send = Callable[[Mail], Awaitable[bool]]


@dataclass(frozen=True)
class DigestWeek:
    week: date
    since: datetime
    web_url: str


@dataclass
class DigestReport:
    enabled: bool
    week_of: date | None = None
    readers: int = 0
    sent: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "weekOf": self.week_of.isoformat() if self.week_of else None,
            "readers": self.readers,
            "sent": self.sent,
            "failed": self.failed,
            "ok": self.failed == 0,
        }


def week_of(now: datetime) -> date:
    day = now.astimezone(INDIA_TZ).date()
    return day - timedelta(days=day.weekday())


def weekly_digest(items: Sequence[AnswerImproved], *, week: date, web_url: str) -> WeeklyDigest:
    return WeeklyDigest(
        schema_version=ALERTS_SCHEMA_VERSION,
        week_of=week,
        items=list(items),
        settings_url=f"{web_url.rstrip('/')}{SETTINGS_PATH}",
    )


def digest_mail(to: str, digest: WeeklyDigest, *, web_url: str) -> Mail:
    lines = ["New cited findings arrived this week for explainers you saved.", ""]
    for item in digest.items:
        lines += [item.question, f"{item.craft.name}: {_news_line(item)}", explainer_url(web_url, item), ""]
    lines.append(f"Stop these emails in Settings: {digest.settings_url}")
    return Mail(to=to, subject=DIGEST_SUBJECT, text="\n".join(lines))


def explainer_url(web_url: str, item: AnswerImproved) -> str:
    return f"{web_url.rstrip('/')}{EXPLAINER_PATH}{item.explainer_id}"


async def send_alert_digests(
    sessions: async_sessionmaker[AsyncSession], *, now: datetime, enabled: bool, web_url: str, send: Send
) -> DigestReport:
    if not enabled:
        return DigestReport(enabled=False)
    digest_week = DigestWeek(week=week_of(now), since=now - DIGEST_WINDOW, web_url=web_url)
    report = DigestReport(enabled=True, week_of=digest_week.week)
    async with sessions() as session:
        readers = await _readers(session, digest_week.week)
    report.readers = len(readers)
    for user_id, email in readers:
        digest = await _claimed_digest(sessions, user_id, digest_week)
        if digest is None:
            continue
        if await send(digest_mail(email, digest, web_url=web_url)):
            report.sent += 1
            continue
        report.failed += 1
        await _released(sessions, user_id, digest_week)
    return report


async def _claimed_digest(
    sessions: async_sessionmaker[AsyncSession], user_id: uuid.UUID, digest_week: DigestWeek
) -> WeeklyDigest | None:
    async with sessions() as session:
        items = await unread_improvements(session, user_id, since=digest_week.since, limit=DIGEST_ITEMS_MAX)
        if not items:
            return None
        digest = weekly_digest(items, week=digest_week.week, web_url=digest_week.web_url)
        claimed = await session.scalar(
            insert(AlertDigestSend)
            .values(userId=user_id, weekOf=digest_week.week, items=len(items))
            .on_conflict_do_nothing(index_elements=["userId", "weekOf"])
            .returning(AlertDigestSend.id)
        )
        await session.commit()
    return digest if claimed is not None else None


async def _released(
    sessions: async_sessionmaker[AsyncSession], user_id: uuid.UUID, digest_week: DigestWeek
) -> None:
    async with sessions() as session:
        await session.execute(
            delete(AlertDigestSend).where(
                AlertDigestSend.userId == user_id, AlertDigestSend.weekOf == digest_week.week
            )
        )
        await session.commit()


async def _readers(session: AsyncSession, week: date) -> list[tuple[uuid.UUID, str]]:
    sent = exists().where(AlertDigestSend.userId == User.id, AlertDigestSend.weekOf == week)
    rows = await session.execute(
        select(User.id, User.email)
        .join(UserPreference, UserPreference.userId == User.id)
        .join(AccessRoster, AccessRoster.email == func.lower(User.email))
        .where(
            UserPreference.alertDigest.is_(True),
            User.deletedAt.is_(None),
            AccessRoster.status == ACTIVE,
            ~sent,
        )
        .order_by(User.id)
    )
    return [(user_id, email) for user_id, email in rows]


def _news_line(item: AnswerImproved) -> str:
    parts = [f"{entry.new_claims} in {DISCIPLINE_TITLES[entry.facet]}" for entry in item.news]
    total = sum(entry.new_claims for entry in item.news)
    noun = "finding" if total == 1 else "findings"
    return f"{total} new {noun} ({', '.join(parts)})"
