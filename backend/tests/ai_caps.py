from typing import Any

from app.core import roles
from app.providers import budget
from app.services import app_settings

__all__ = ["ALLOWANCES_AN_OWNER_MIGHT_SET", "CAPS_AN_OWNER_MIGHT_SET", "ceilings", "unlimited"]

CAPS_AN_OWNER_MIGHT_SET: dict[str, Any] = {
    app_settings.MONTHLY_CEILING_USD: 800.0,
    app_settings.MEDIA_CAP_USD: 150.0,
    app_settings.ROLE_DAILY_USD: {
        "STUDENT": 0.5,
        "ARTISAN": None,
        "RESEARCHER": 3.0,
        "PROFESSOR": 5.0,
        "ADMIN": 10.0,
        "MASTER_ADMIN": None,
    },
    app_settings.DEGRADE_AT_FRACTION: 0.8,
    app_settings.ANSWER_CAP_USD: {"BASIC": 0.25, "DETAILED": 1.0, "EXPERT": 2.5},
}
ALLOWANCES_AN_OWNER_MIGHT_SET: dict[str, dict[str, int | None]] = {
    roles.STUDENT: {"VOICE_SECONDS": 600, "IMAGE": 5, "VIDEO": 0},
    roles.ARTISAN: {"VOICE_SECONDS": None, "IMAGE": None, "VIDEO": None},
    roles.RESEARCHER: {"VOICE_SECONDS": 1800, "IMAGE": 30, "VIDEO": 5},
    roles.PROFESSOR: {"VOICE_SECONDS": 1800, "IMAGE": 50, "VIDEO": 10},
    roles.ADMIN: {"VOICE_SECONDS": 3600, "IMAGE": 100, "VIDEO": 20},
    roles.MASTER_ADMIN: {"VOICE_SECONDS": None, "IMAGE": None, "VIDEO": None},
}


def unlimited(**overrides: object) -> budget.Ceilings:
    values = dict(app_settings.DEFAULTS)
    values.update(overrides)
    return budget.Ceilings.from_settings(values)


def ceilings(**overrides: object) -> budget.Ceilings:
    values = {**app_settings.DEFAULTS, **CAPS_AN_OWNER_MIGHT_SET}
    values.update(overrides)
    return budget.Ceilings.from_settings(values)
