from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_admin_role"
down_revision: str | Sequence[str] | None = "0008_media_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMIN = "ADMIN"
DEMOTED_TO = "PROFESSOR"

ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (("UserRole", ("ADMIN",)),)

USER_ROLES_BEFORE = ("MASTER_ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT")

ADMIN_QUOTAS: tuple[tuple[str, int], ...] = (("VOICE_SECONDS", 3600), ("IMAGE", 100), ("VIDEO", 20))

ROLE_DAILY_USD_KEY = "AI_ROLE_DAILY_USD"
ADMIN_DAILY_USD = 10.0

ROLE_COLUMNS: tuple[tuple[str, str, str | None], ...] = (
    ("User", "role", "STUDENT"),
    ("AccessRoster", "admitRole", None),
    ("Invite", "role", None),
    ("RoleRequest", "requestedRole", None),
    ("UsageEvent", "role", None),
    ("QuotaPolicy", "role", None),
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for enum_name, values in ENUM_ADDITIONS:
            for value in values:
                op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")
    for resource, per_day in ADMIN_QUOTAS:
        op.execute(
            sa.text(
                'INSERT INTO "QuotaPolicy" (role, resource, "perDay") '
                'VALUES (CAST(:role AS "UserRole"), CAST(:resource AS "QuotaResource"), :perDay) '
                "ON CONFLICT (role, resource) DO NOTHING"
            ).bindparams(role=ADMIN, resource=resource, perDay=per_day)
        )
    op.execute(
        sa.text(
            'UPDATE "AppSetting" SET value = value || '
            "jsonb_build_object(CAST(:role AS text), CAST(:cap AS numeric)) "
            "WHERE key = :key AND jsonb_typeof(value) = 'object' AND NOT (value ? CAST(:role AS text))"
        ).bindparams(role=ADMIN, cap=ADMIN_DAILY_USD, key=ROLE_DAILY_USD_KEY)
    )


def downgrade() -> None:
    op.execute(sa.text('DELETE FROM "QuotaPolicy" WHERE role::text = :role').bindparams(role=ADMIN))
    op.execute(
        sa.text('UPDATE "AppSetting" SET value = value - CAST(:role AS text) WHERE key = :key').bindparams(
            role=ADMIN, key=ROLE_DAILY_USD_KEY
        )
    )
    op.execute('ALTER TYPE "UserRole" RENAME TO "UserRole_before_0009"')
    listed = ", ".join(f"'{value}'" for value in USER_ROLES_BEFORE)
    op.execute(f'CREATE TYPE "UserRole" AS ENUM ({listed})')
    for table, column, default in ROLE_COLUMNS:
        if default is not None:
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP DEFAULT')
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE "UserRole" USING '
            f"(CASE WHEN \"{column}\"::text = '{ADMIN}' THEN '{DEMOTED_TO}' "
            f'ELSE "{column}"::text END)::"UserRole"'
        )
        if default is not None:
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT \'{default}\'')
    op.execute('DROP TYPE "UserRole_before_0009"')
