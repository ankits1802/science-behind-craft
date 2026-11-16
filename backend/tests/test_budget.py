from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.providers import budget
from app.services import app_settings
from app.services.ai_providers import model_for


def ceilings(**overrides: object) -> budget.Ceilings:
    values = dict(app_settings.DEFAULTS)
    values.update(overrides)
    return budget.Ceilings.from_settings(values)


def test_defaults_are_the_owner_ceilings() -> None:
    c = ceilings()
    assert c.monthly_usd == Decimal("800")
    assert c.media_usd == Decimal("150")
    assert c.degrade_at == Decimal("0.8")


def test_allows_inside_every_cap() -> None:
    decision = budget.evaluate(
        ceilings(),
        budget.SpendState(Decimal("100"), Decimal("10"), Decimal("0.1")),
        estimate_usd=Decimal("0.05"),
        is_media=False,
        role="STUDENT",
    )
    assert decision.allowed
    assert not decision.degrade


def test_monthly_ceiling_refuses() -> None:
    decision = budget.evaluate(
        ceilings(),
        budget.SpendState(Decimal("799.99"), Decimal(0), Decimal(0)),
        estimate_usd=Decimal("0.02"),
        is_media=False,
        role="MASTER_ADMIN",
    )
    assert not decision.allowed
    assert decision.reason == budget.MONTHLY_CEILING
    assert decision.degrade
    assert decision.message


def test_exactly_at_ceiling_is_allowed() -> None:
    decision = budget.evaluate(
        ceilings(),
        budget.SpendState(Decimal("799.98"), Decimal(0), Decimal(0)),
        estimate_usd=Decimal("0.02"),
        is_media=False,
        role="MASTER_ADMIN",
    )
    assert decision.allowed


def test_media_sub_cap_refuses_media_only() -> None:
    spend = budget.SpendState(Decimal("300"), Decimal("149.95"), Decimal(0))
    media = budget.evaluate(
        ceilings(), spend, estimate_usd=Decimal("0.067"), is_media=True, role="MASTER_ADMIN"
    )
    text = budget.evaluate(
        ceilings(), spend, estimate_usd=Decimal("0.067"), is_media=False, role="MASTER_ADMIN"
    )
    assert not media.allowed
    assert media.reason == budget.MEDIA_CAP
    assert text.allowed


def test_role_daily_cap() -> None:
    spend = budget.SpendState(Decimal("10"), Decimal(0), Decimal("0.49"))
    student = budget.evaluate(ceilings(), spend, estimate_usd=Decimal("0.02"), is_media=False, role="STUDENT")
    researcher = budget.evaluate(
        ceilings(), spend, estimate_usd=Decimal("0.02"), is_media=False, role="RESEARCHER"
    )
    master = budget.evaluate(
        ceilings(),
        budget.SpendState(Decimal(10), Decimal(0), Decimal(500)),
        estimate_usd=Decimal("1"),
        is_media=False,
        role="MASTER_ADMIN",
    )
    assert not student.allowed
    assert student.reason == budget.ROLE_DAILY_CAP
    assert researcher.allowed
    assert master.allowed


def test_admin_daily_cap_is_ten_dollars() -> None:
    def admin_spending(today: str) -> budget.BudgetDecision:
        spend = budget.SpendState(Decimal(10), Decimal(0), Decimal(today))
        return budget.evaluate(ceilings(), spend, estimate_usd=Decimal("0.5"), is_media=False, role="ADMIN")

    assert admin_spending("9.5").allowed
    assert admin_spending("9.51").reason == budget.ROLE_DAILY_CAP


def test_unknown_role_falls_back_to_student_cap() -> None:
    spend = budget.SpendState(Decimal(0), Decimal(0), Decimal("0.5"))
    decision = budget.evaluate(ceilings(), spend, estimate_usd=Decimal("0.01"), is_media=False, role="GUEST")
    assert decision.reason == budget.ROLE_DAILY_CAP


def test_degrade_at_eighty_percent() -> None:
    below = budget.evaluate(
        ceilings(),
        budget.SpendState(Decimal("639.99")),
        estimate_usd=Decimal("0.01"),
        is_media=False,
        role=None,
    )
    above = budget.evaluate(
        ceilings(), budget.SpendState(Decimal("640")), estimate_usd=Decimal("0.01"), is_media=False, role=None
    )
    assert not below.degrade
    assert above.degrade
    assert above.allowed


def test_zero_ceiling_refuses_paid_but_not_free() -> None:
    c = ceilings(**{app_settings.MONTHLY_CEILING_USD: 0})
    paid = budget.evaluate(
        c, budget.SpendState(), estimate_usd=Decimal("0.000001"), is_media=False, role=None
    )
    free = budget.evaluate(c, budget.SpendState(), estimate_usd=Decimal(0), is_media=False, role=None)
    assert not paid.allowed
    assert free.allowed


def test_request_budget() -> None:
    decision = budget.evaluate(
        ceilings(),
        budget.SpendState(),
        estimate_usd=Decimal("2.5"),
        is_media=False,
        role="MASTER_ADMIN",
        request_budget_usd=Decimal("2"),
    )
    assert decision.reason == budget.REQUEST_BUDGET


def test_token_cost_sonnet() -> None:
    model = model_for("ANTHROPIC", "claude-sonnet-5-5")
    cost = budget.token_cost(model, input_tokens=12_000, output_tokens=1_200, day=date(2026, 11, 16))
    assert cost == Decimal("0.036000")


def test_cached_tokens_are_cheaper() -> None:
    model = model_for("ANTHROPIC", "claude-sonnet-5-5")
    full = budget.token_cost(model, input_tokens=10_000, output_tokens=0, day=date(2026, 11, 16))
    cached = budget.token_cost(
        model, input_tokens=10_000, output_tokens=0, cached_tokens=8_000, day=date(2026, 11, 16)
    )
    assert cached < full
    assert cached == Decimal("0.008000")


def test_gemini_flash_price_doubles_in_2027() -> None:
    model = model_for("GEMINI", "gemini-3.8-flash")
    before = budget.token_cost(model, input_tokens=1_000_000, output_tokens=0, day=date(2026, 12, 31))
    after = budget.token_cost(model, input_tokens=1_000_000, output_tokens=0, day=date(2027, 1, 1))
    assert before == Decimal("0.750000")
    assert after == Decimal("1.500000")


def test_unknown_price_is_conservative() -> None:
    unverified = model_for("DEEPSEEK", "deepseek-flash")
    cost = budget.token_cost(unverified, input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == Decimal("35.000000")


def test_override_price_wins() -> None:
    model = model_for("DEEPSEEK", "deepseek-flash")
    cost = budget.token_cost(
        model, input_tokens=1_000_000, output_tokens=0, overrides={"deepseek-flash": {"in": 0.07, "out": 1.1}}
    )
    assert cost == Decimal("0.070000")


def test_unit_costs() -> None:
    image = model_for("GEMINI", "gemini-3.1-flash-image")
    video = model_for("GEMINI", "gemini-omni-1.2-flash")
    assert budget.unit_cost(image, 1) == Decimal("0.067000")
    assert budget.unit_cost(video, 8) == Decimal("0.560000")


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(2026, 11, 30, 18, 29, tzinfo=UTC), datetime(2026, 10, 31, 18, 30, tzinfo=UTC)),
        (datetime(2026, 11, 30, 18, 31, tzinfo=UTC), datetime(2026, 11, 30, 18, 30, tzinfo=UTC)),
    ],
)
def test_month_starts_at_ist_midnight(moment: datetime, expected: datetime) -> None:
    assert budget.month_start(moment) == expected


def test_day_starts_at_ist_midnight() -> None:
    assert budget.day_start(datetime(2026, 11, 16, 3, 0, tzinfo=UTC)) == datetime(
        2026, 11, 15, 18, 30, tzinfo=UTC
    )
