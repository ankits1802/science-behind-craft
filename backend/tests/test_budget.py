from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.providers import budget
from app.schemas.admin import AppSettingsUpdate
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
        role="ADMIN",
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
        role="ADMIN",
    )
    assert decision.allowed


def test_media_sub_cap_refuses_media_only() -> None:
    spend = budget.SpendState(Decimal("300"), Decimal("149.95"), Decimal(0))
    media = budget.evaluate(ceilings(), spend, estimate_usd=Decimal("0.067"), is_media=True, role="ADMIN")
    text = budget.evaluate(ceilings(), spend, estimate_usd=Decimal("0.067"), is_media=False, role="ADMIN")
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
        role="ADMIN",
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


AT_THE_CEILING = budget.SpendState(Decimal("800"), Decimal("150"), Decimal("500"))


@pytest.mark.parametrize("is_media", [False, True])
def test_a_master_admin_is_never_refused_or_degraded_at_the_ceiling(is_media: bool) -> None:
    decision = budget.evaluate(
        ceilings(), AT_THE_CEILING, estimate_usd=Decimal("3"), is_media=is_media, role="MASTER_ADMIN"
    )
    assert (decision.allowed, decision.reason, decision.degrade) == (True, None, False)
    assert decision.month_fraction == Decimal(1)
    assert not budget.degrades(ceilings(), AT_THE_CEILING, role="MASTER_ADMIN")


@pytest.mark.parametrize("role", ["STUDENT", "ADMIN", None])
def test_everyone_else_is_refused_and_degraded_at_the_ceiling(role: str | None) -> None:
    decision = budget.evaluate(
        ceilings(), AT_THE_CEILING, estimate_usd=Decimal("0.01"), is_media=False, role=role
    )
    assert (decision.allowed, decision.reason, decision.degrade) == (False, budget.MONTHLY_CEILING, True)
    assert budget.degrades(ceilings(), AT_THE_CEILING, role=role)


def test_a_master_admin_daily_cap_in_settings_is_ignored() -> None:
    capped = ceilings(**{app_settings.ROLE_DAILY_USD: {"MASTER_ADMIN": 1.0, "STUDENT": 0.5}})
    spend = budget.SpendState(Decimal(10), Decimal(0), Decimal(5))
    master = budget.evaluate(capped, spend, estimate_usd=Decimal("2"), is_media=False, role="MASTER_ADMIN")
    assert master.allowed


def test_a_master_admin_answer_has_no_cap() -> None:
    decision = budget.evaluate(
        ceilings(),
        budget.SpendState(),
        estimate_usd=Decimal("40"),
        is_media=False,
        role="MASTER_ADMIN",
        answer_left_usd=Decimal(0),
        request_budget_usd=Decimal(1),
    )
    assert decision.allowed


def test_the_answer_caps_per_depth_are_ai_budget_settings() -> None:
    assert app_settings.DEFAULTS[app_settings.ANSWER_CAP_USD] == {
        "BASIC": 0.25,
        "DETAILED": 0.5,
        "EXPERT": 1.0,
    }
    assert ceilings().answer_usd == {
        "BASIC": Decimal("0.25"),
        "DETAILED": Decimal("0.5"),
        "EXPERT": Decimal("1"),
    }
    view = app_settings.public_view(dict(app_settings.DEFAULTS))
    assert view["answerCapUsd"] == {"BASIC": 0.25, "DETAILED": 0.5, "EXPERT": 1.0}


def test_an_answer_is_refused_past_its_depth_cap() -> None:
    spent = budget.AnswerSpend(depth="EXPERT")
    spent.hold(Decimal("0.3"))
    spent.settle(Decimal("0.3"), Decimal("0.25"))
    spent.hold(Decimal("0.5"))
    assert spent.left(ceilings()) == Decimal("0.25")
    inside = budget.evaluate(
        ceilings(),
        budget.SpendState(),
        estimate_usd=Decimal("0.25"),
        is_media=False,
        role="ADMIN",
        answer_left_usd=spent.left(ceilings()),
    )
    past = budget.evaluate(
        ceilings(),
        budget.SpendState(),
        estimate_usd=Decimal("0.26"),
        is_media=False,
        role="ADMIN",
        answer_left_usd=spent.left(ceilings()),
    )
    assert inside.allowed
    assert (past.allowed, past.reason) == (False, budget.ANSWER_CAP)
    assert past.message == "This answer reached the cost limit for its depth."


def test_a_released_hold_frees_the_answer_cap() -> None:
    spent = budget.AnswerSpend(depth="BASIC")
    spent.hold(Decimal("0.2"))
    assert spent.left(ceilings()) == Decimal("0.05")
    spent.release(Decimal("0.2"))
    assert spent.left(ceilings()) == Decimal("0.25")


def test_a_depth_without_a_cap_leaves_nothing_to_spend() -> None:
    capped = ceilings(**{app_settings.ANSWER_CAP_USD: {"BASIC": 0.25}})
    assert budget.AnswerSpend(depth="EXPERT").left(capped) == Decimal(0)


def test_budget_changes_merge_answer_caps_by_depth() -> None:
    current = dict(app_settings.DEFAULTS)
    changes = app_settings.budget_changes({"answerCapUsd": {"EXPERT": 2.0}}, current)
    assert changes == {app_settings.ANSWER_CAP_USD: {"BASIC": 0.25, "DETAILED": 0.5, "EXPERT": 2.0}}


def test_budget_changes_refuse_a_master_admin_cap() -> None:
    current = dict(app_settings.DEFAULTS)
    with pytest.raises(InvalidInput, match="Master Admins have no caps"):
        app_settings.budget_changes({"roleDailyUsd": {"MASTER_ADMIN": 5.0}}, current)
    allowed = app_settings.budget_changes({"roleDailyUsd": {"MASTER_ADMIN": None, "ADMIN": 12.0}}, current)
    assert allowed == {app_settings.ROLE_DAILY_USD: {"MASTER_ADMIN": None, "ADMIN": 12.0}}


def test_budget_changes_refuse_unknown_roles_and_a_media_cap_over_the_ceiling() -> None:
    current = dict(app_settings.DEFAULTS)
    with pytest.raises(InvalidInput, match="Unknown roles: GUEST"):
        app_settings.budget_changes({"roleDailyUsd": {"GUEST": 1.0}}, current)
    with pytest.raises(InvalidInput, match="media cap"):
        app_settings.budget_changes({"monthlyCeilingUsd": 100.0}, current)
    assert app_settings.budget_changes({"domainAllowlist": [" IITB.ac.in", "iitb.ac.in", " "]}, current) == {
        app_settings.DOMAIN_ALLOWLIST: ["iitb.ac.in"]
    }


def test_the_budget_update_body_takes_answer_caps_for_the_three_depths_only() -> None:
    assert AppSettingsUpdate(answerCapUsd={"BASIC": 0.1}).answerCapUsd == {"BASIC": 0.1}
    with pytest.raises(ValidationError):
        AppSettingsUpdate(answerCapUsd={"DEEP": 0.1})
    with pytest.raises(ValidationError):
        AppSettingsUpdate(answerCapUsd={"EXPERT": -1})
