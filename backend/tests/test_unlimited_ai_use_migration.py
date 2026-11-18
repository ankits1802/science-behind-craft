from app.services import app_settings

from .migration_scripts import migration

STEP = migration("0029_unlimited_ai_use")


def test_the_step_follows_the_roles_and_contributions_migration() -> None:
    assert (STEP.revision, STEP.down_revision) == ("0029_unlimited_ai_use", "0028_roles_and_contributions")


def test_the_step_drops_exactly_the_stored_ai_budget_caps() -> None:
    assert set(STEP.CAP_SETTINGS) == {
        app_settings.MONTHLY_CEILING_USD,
        app_settings.MEDIA_CAP_USD,
        app_settings.ROLE_DAILY_USD,
        app_settings.DEGRADE_AT_FRACTION,
        app_settings.ANSWER_CAP_USD,
    }
    assert STEP.DROP_CAP_SETTINGS == (
        "DELETE FROM \"AppSetting\" WHERE key IN ('AI_MONTHLY_CEILING_USD', 'AI_MEDIA_CAP_USD', "
        "'AI_ROLE_DAILY_USD', 'AI_DEGRADE_AT_FRACTION', 'AI_ANSWER_CAP_USD')"
    )


def test_every_statement_converges_so_a_second_run_changes_nothing() -> None:
    drop, quotas, routes = STEP.UPGRADE_STATEMENTS
    assert drop.startswith('DELETE FROM "AppSetting" WHERE key IN (')
    assert quotas.endswith('WHERE "perDay" IS NOT NULL OR "perMonth" IS NOT NULL')
    assert '"perDay" = NULL, "perMonth" = NULL' in quotas
    assert routes.endswith('WHERE "maxOutputTokens" IS NOT NULL')
    assert '"maxOutputTokens" = NULL' in routes


def test_with_the_rows_gone_the_defaults_are_unlimited() -> None:
    view = app_settings.public_view(dict(app_settings.DEFAULTS))
    assert {key: view[key] for key in ("monthlyCeilingUsd", "mediaCapUsd", "degradeAtFraction")} == {
        "monthlyCeilingUsd": None,
        "mediaCapUsd": None,
        "degradeAtFraction": None,
    }
