import re
from datetime import UTC, date, datetime, time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require
from app.core.roles import Capability, daily_allowance
from app.models import UsageEvent, User
from app.providers import budget
from app.providers.router import Principal, current_spend
from app.services import app_settings

router = APIRouter(prefix="/usage", tags=["usage"])

usage_reader = require(Capability.VIEW_USAGE)

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _month_bounds(month: str | None) -> tuple[str, datetime, datetime]:
    if month is None:
        start = budget.month_start()
        local = start.astimezone(budget.BUDGET_TIMEZONE)
        label = f"{local.year:04d}-{local.month:02d}"
    else:
        if not MONTH_PATTERN.fullmatch(month):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "month must look like 2026-11")
        label = month
        year, number = int(month[:4]), int(month[5:])
        start = datetime.combine(date(year, number, 1), time.min, tzinfo=budget.BUDGET_TIMEZONE).astimezone(
            UTC
        )
    local = start.astimezone(budget.BUDGET_TIMEZONE)
    next_year, next_month = (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
    end = datetime.combine(
        date(next_year, next_month, 1), time.min, tzinfo=budget.BUDGET_TIMEZONE
    ).astimezone(UTC)
    return label, start, end


def _money(value: Any) -> float:
    return float(budget.usd(value))


@router.get("/summary")
async def usage_summary(
    month: str | None = Query(default=None),
    _: User = Depends(usage_reader),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    label, start, end = _month_bounds(month)
    window = (UsageEvent.createdAt >= start, UsageEvent.createdAt < end)
    settled = UsageEvent.outcome != "RESERVED"
    settings_values = await app_settings.load_all(session)
    ceilings = budget.Ceilings.from_settings(settings_values)

    async def grouped(column: Any) -> list[dict[str, Any]]:
        rows = (
            await session.execute(
                select(
                    column,
                    func.coalesce(func.sum(UsageEvent.costUsd), 0),
                    func.count(),
                    func.coalesce(func.sum(UsageEvent.inputTokens), 0),
                    func.coalesce(func.sum(UsageEvent.outputTokens), 0),
                    func.sum(case((UsageEvent.outcome == "OK", 1), else_=0)),
                )
                .where(*window, settled)
                .group_by(column)
                .order_by(func.sum(UsageEvent.costUsd).desc())
            )
        ).all()
        return [
            {
                "key": key,
                "costUsd": _money(cost),
                "calls": calls,
                "inputTokens": int(tin),
                "outputTokens": int(tout),
                "ok": int(ok or 0),
            }
            for key, cost, calls, tin, tout, ok in rows
        ]

    totals = (
        await session.execute(
            select(
                func.coalesce(func.sum(UsageEvent.costUsd), 0),
                func.coalesce(func.sum(case((UsageEvent.isMedia.is_(True), UsageEvent.costUsd), else_=0)), 0),
                func.sum(case((UsageEvent.outcome == "REFUSED_CEILING", 1), else_=0)),
                func.sum(case((UsageEvent.outcome == "ERROR", 1), else_=0)),
                func.count(),
            ).where(*window, settled)
        )
    ).one()
    reserved = (
        await session.execute(
            select(func.coalesce(func.sum(UsageEvent.estimatedCostUsd), 0)).where(
                *window, UsageEvent.outcome == "RESERVED"
            )
        )
    ).scalar_one()
    day = func.date_trunc("day", func.timezone("Asia/Kolkata", UsageEvent.createdAt))
    by_day = (
        await session.execute(
            select(day, func.coalesce(func.sum(UsageEvent.costUsd), 0), func.count())
            .where(*window, settled)
            .group_by(day)
            .order_by(day)
        )
    ).all()
    spent = budget.usd(totals[0])
    fraction = float(spent / ceilings.monthly_usd) if ceilings.monthly_usd > 0 else 1.0
    top_users = (
        await session.execute(
            select(User.id, User.name, User.email, User.role, func.sum(UsageEvent.costUsd), func.count())
            .join(User, User.id == UsageEvent.userId)
            .where(*window, settled)
            .group_by(User.id, User.name, User.email, User.role)
            .order_by(func.sum(UsageEvent.costUsd).desc())
            .limit(20)
        )
    ).all()
    return {
        "month": label,
        "monthlyCeilingUsd": float(ceilings.monthly_usd),
        "mediaCapUsd": float(ceilings.media_usd),
        "spentUsd": float(spent),
        "mediaSpentUsd": _money(totals[1]),
        "reservedUsd": _money(reserved),
        "fraction": round(fraction, 4),
        "degraded": fraction >= float(ceilings.degrade_at),
        "calls": int(totals[4] or 0),
        "refusedCalls": int(totals[2] or 0),
        "failedCalls": int(totals[3] or 0),
        "byTask": await grouped(UsageEvent.task),
        "byProvider": await grouped(UsageEvent.provider),
        "byModel": await grouped(UsageEvent.model),
        "byRole": await grouped(UsageEvent.role),
        "byDay": [
            {"day": d.date().isoformat(), "costUsd": _money(cost), "calls": calls}
            for d, cost, calls in by_day
        ],
        "topUsers": [
            {
                "userId": str(uid),
                "name": name,
                "email": email,
                "role": role,
                "costUsd": _money(cost),
                "calls": calls,
            }
            for uid, name, email, role, cost, calls in top_users
        ],
    }


@router.get("/me")
async def my_usage(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    settings_values = await app_settings.load_all(session)
    ceilings = budget.Ceilings.from_settings(settings_values)
    spend = await current_spend(session, Principal(user_id=user.id, role=user.role))
    cap = ceilings.role_daily_usd.get(user.role)
    return {
        "todayUsd": float(spend.user_day_usd),
        "dailyCapUsd": float(cap) if cap is not None else None,
        "allowances": {
            resource: daily_allowance(user, resource) for resource in ("VOICE_SECONDS", "IMAGE", "VIDEO")
        },
        "platformDegraded": budget.month_fraction(ceilings, spend) >= ceilings.degrade_at,
    }
