from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.services.ai_providers import UNKNOWN_TOKEN_PRICE, UNKNOWN_UNIT_PRICE, AiModel

BUDGET_TIMEZONE = ZoneInfo("Asia/Kolkata")
CACHED_INPUT_FRACTION = Decimal("0.25")
RESERVATION_TTL = timedelta(minutes=15)
MICRO = Decimal("0.000001")
MILLION = Decimal(1_000_000)

MONTHLY_CEILING = "MONTHLY_CEILING"
MEDIA_CAP = "MEDIA_CAP"
ROLE_DAILY_CAP = "ROLE_DAILY_CAP"
REQUEST_BUDGET = "REQUEST_BUDGET"

REFUSAL_MESSAGES = {
    MONTHLY_CEILING: "The monthly AI budget has been reached. Verified answers from stored knowledge still work.",
    MEDIA_CAP: "The monthly budget for images and video has been reached.",
    ROLE_DAILY_CAP: "You have reached today's AI allowance for your role. It resets at midnight IST.",
    REQUEST_BUDGET: "This request would cost more than its budget allows.",
}


def usd(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(MICRO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Ceilings:
    monthly_usd: Decimal
    media_usd: Decimal
    role_daily_usd: dict[str, Decimal | None]
    degrade_at: Decimal

    @classmethod
    def from_settings(cls, values: dict[str, Any]) -> Ceilings:
        from app.services import app_settings as keys

        role_caps = values.get(keys.ROLE_DAILY_USD) or {}
        return cls(
            monthly_usd=usd(values.get(keys.MONTHLY_CEILING_USD, 0)),
            media_usd=usd(values.get(keys.MEDIA_CAP_USD, 0)),
            role_daily_usd={role: (None if cap is None else usd(cap)) for role, cap in role_caps.items()},
            degrade_at=Decimal(str(values.get(keys.DEGRADE_AT_FRACTION, 0.8))),
        )


@dataclass(frozen=True)
class SpendState:
    month_usd: Decimal = Decimal(0)
    media_month_usd: Decimal = Decimal(0)
    user_day_usd: Decimal = Decimal(0)


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    reason: str | None
    degrade: bool
    month_fraction: Decimal

    @property
    def message(self) -> str | None:
        return REFUSAL_MESSAGES.get(self.reason or "")


def month_fraction(ceilings: Ceilings, spend: SpendState) -> Decimal:
    if ceilings.monthly_usd <= 0:
        return Decimal(1)
    return spend.month_usd / ceilings.monthly_usd


def evaluate(
    ceilings: Ceilings,
    spend: SpendState,
    *,
    estimate_usd: Decimal,
    is_media: bool,
    role: str | None,
    request_budget_usd: Decimal | None = None,
) -> BudgetDecision:
    fraction = month_fraction(ceilings, spend)
    degrade = fraction >= ceilings.degrade_at

    def refuse(reason: str) -> BudgetDecision:
        return BudgetDecision(False, reason, degrade, fraction)

    if estimate_usd <= 0:
        return BudgetDecision(True, None, degrade, fraction)
    if request_budget_usd is not None and estimate_usd > request_budget_usd:
        return refuse(REQUEST_BUDGET)
    if spend.month_usd + estimate_usd > ceilings.monthly_usd:
        return refuse(MONTHLY_CEILING)
    if is_media and spend.media_month_usd + estimate_usd > ceilings.media_usd:
        return refuse(MEDIA_CAP)
    cap = ceilings.role_daily_usd.get(role or "", None) if role else None
    if role and role not in ceilings.role_daily_usd:
        cap = ceilings.role_daily_usd.get("STUDENT")
    if cap is not None and spend.user_day_usd + estimate_usd > cap:
        return refuse(ROLE_DAILY_CAP)
    return BudgetDecision(True, None, degrade, fraction)


def token_price(
    model: AiModel | None, day: date, overrides: dict[str, Any] | None = None
) -> tuple[Decimal, Decimal]:
    override = (overrides or {}).get(model.id) if model else None
    if isinstance(override, dict) and "in" in override and "out" in override:
        return Decimal(str(override["in"])), Decimal(str(override["out"]))
    price = model.token_price_on(day) if model else None
    chosen = price if price is not None else UNKNOWN_TOKEN_PRICE
    return Decimal(str(chosen[0])), Decimal(str(chosen[1]))


def unit_price(model: AiModel | None, overrides: dict[str, Any] | None = None) -> tuple[Decimal, str]:
    override = (overrides or {}).get(model.id) if model else None
    unit = (model.unit if model else None) or "image"
    if isinstance(override, dict) and "unit" in override:
        return Decimal(str(override["unit"])), unit
    if model is not None and model.price_per_unit is not None:
        return Decimal(str(model.price_per_unit)), unit
    return Decimal(str(UNKNOWN_UNIT_PRICE.get(unit, UNKNOWN_UNIT_PRICE["image"]))), unit


def token_cost(
    model: AiModel | None,
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    cached_tokens: int | None = None,
    day: date | None = None,
    overrides: dict[str, Any] | None = None,
) -> Decimal:
    price_in, price_out = token_price(model, day or budget_today(), overrides)
    total_in = Decimal(max(0, input_tokens or 0))
    cached = min(Decimal(max(0, cached_tokens or 0)), total_in)
    billed_in = (total_in - cached) * price_in + cached * price_in * CACHED_INPUT_FRACTION
    billed_out = Decimal(max(0, output_tokens or 0)) * price_out
    return usd((billed_in + billed_out) / MILLION)


def unit_cost(model: AiModel | None, units: float, overrides: dict[str, Any] | None = None) -> Decimal:
    price, _unit = unit_price(model, overrides)
    return usd(price * Decimal(str(max(0.0, units))))


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def budget_today(now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(BUDGET_TIMEZONE).date()


def month_start(now: datetime | None = None) -> datetime:
    local = (now or datetime.now(UTC)).astimezone(BUDGET_TIMEZONE)
    return datetime.combine(local.date().replace(day=1), time.min, tzinfo=BUDGET_TIMEZONE).astimezone(UTC)


def day_start(now: datetime | None = None) -> datetime:
    local = (now or datetime.now(UTC)).astimezone(BUDGET_TIMEZONE)
    return datetime.combine(local.date(), time.min, tzinfo=BUDGET_TIMEZONE).astimezone(UTC)
