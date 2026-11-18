from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_unlimited_ai_use"
down_revision: str | Sequence[str] | None = "0028_roles_and_contributions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CAP_SETTINGS: tuple[str, ...] = (
    "AI_MONTHLY_CEILING_USD",
    "AI_MEDIA_CAP_USD",
    "AI_ROLE_DAILY_USD",
    "AI_DEGRADE_AT_FRACTION",
    "AI_ANSWER_CAP_USD",
)

EARLIER_QUOTAS: tuple[tuple[str, str, int], ...] = (
    ("STUDENT", "VOICE_SECONDS", 600),
    ("STUDENT", "IMAGE", 5),
    ("STUDENT", "VIDEO", 0),
    ("RESEARCHER", "VOICE_SECONDS", 1800),
    ("RESEARCHER", "IMAGE", 30),
    ("RESEARCHER", "VIDEO", 5),
    ("PROFESSOR", "VOICE_SECONDS", 1800),
    ("PROFESSOR", "IMAGE", 50),
    ("PROFESSOR", "VIDEO", 10),
    ("ADMIN", "VOICE_SECONDS", 3600),
    ("ADMIN", "IMAGE", 100),
    ("ADMIN", "VIDEO", 20),
)

EARLIER_ROUTE_TOKENS: tuple[tuple[str, int], ...] = (("TRANSLATE", 8192), ("SUMMARISE", 2048))

DROP_CAP_SETTINGS = 'DELETE FROM "AppSetting" WHERE key IN ({keys})'.format(
    keys=", ".join(f"'{key}'" for key in CAP_SETTINGS)
)
UNLIMITED_QUOTAS = (
    'UPDATE "QuotaPolicy" SET "perDay" = NULL, "perMonth" = NULL, "updatedAt" = now() '
    'WHERE "perDay" IS NOT NULL OR "perMonth" IS NOT NULL'
)
MODEL_MAXIMUM_ROUTES = (
    'UPDATE "RoutePolicy" SET "maxOutputTokens" = NULL, "updatedAt" = now() '
    'WHERE "maxOutputTokens" IS NOT NULL'
)
RESTORE_QUOTA = (
    'UPDATE "QuotaPolicy" SET "perDay" = :perDay, "updatedAt" = now() '
    'WHERE role = CAST(:role AS "UserRole") AND resource = CAST(:resource AS "QuotaResource") '
    'AND "perDay" IS NULL'
)
RESTORE_ROUTE_TOKENS = (
    'UPDATE "RoutePolicy" SET "maxOutputTokens" = :tokens, "updatedAt" = now() '
    'WHERE task = CAST(:task AS "AiTask") AND "maxOutputTokens" IS NULL'
)


UPGRADE_STATEMENTS: tuple[str, ...] = (DROP_CAP_SETTINGS, UNLIMITED_QUOTAS, MODEL_MAXIMUM_ROUTES)


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for role, resource, per_day in EARLIER_QUOTAS:
        op.execute(sa.text(RESTORE_QUOTA).bindparams(role=role, resource=resource, perDay=per_day))
    for task, tokens in EARLIER_ROUTE_TOKENS:
        op.execute(sa.text(RESTORE_ROUTE_TOKENS).bindparams(task=task, tokens=tokens))
