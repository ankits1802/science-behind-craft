from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0123_mcp_tasks"
down_revision: str | Sequence[str] | None = "0121_coded_figures"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "McpTask"
TASK_ID_CHARS = 64
TOOL_NAME_CHARS = 64
DIGEST_CHARS = 64
STATUS_CHARS = 16
MESSAGE_CHARS = 300
STATUSES = ("working", "completed", "failed", "cancelled")
STAMP = sa.DateTime(timezone=True)
REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "McpTask" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        "McpTask",
        sa.Column("id", sa.String(length=TASK_ID_CHARS), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("tool", sa.String(length=TOOL_NAME_CHARS), nullable=False),
        sa.Column("argumentsHash", sa.String(length=DIGEST_CHARS), nullable=False),
        sa.Column("status", sa.String(length=STATUS_CHARS), nullable=False),
        sa.Column("statusMessage", sa.String(length=MESSAGE_CHARS), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", postgresql.JSONB(), nullable=True),
        sa.Column("createdAt", STAMP, nullable=False),
        sa.Column("updatedAt", STAMP, nullable=False),
        sa.Column("heartbeatAt", STAMP, nullable=False),
        sa.Column("expiresAt", STAMP, nullable=False),
        sa.CheckConstraint(_listed("status", STATUSES), name=op.f(f"{TABLE}_status_check")),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f(f"{TABLE}_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
    )
    op.create_index(op.f(f"{TABLE}_userId_expiresAt_idx"), TABLE, ["userId", "expiresAt"])
    op.create_index(op.f(f"{TABLE}_expiresAt_idx"), TABLE, ["expiresAt"])
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    op.drop_table(TABLE)


def _listed(column: str, values: Sequence[str]) -> str:
    named = ", ".join(f"'{value}'" for value in values)
    return f'"{column}" IN ({named})'
