from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039_upkeep"
down_revision: str | Sequence[str] | None = "0038_open_work"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "SourceUpkeep"
STAMP = sa.DateTime(timezone=True)
FETCH_OUTCOMES = ("FETCHED", "REFUSED", "FAILED")

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "SourceUpkeep" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        "SourceUpkeep",
        sa.Column("sourceId", sa.UUID(), nullable=False),
        sa.Column("checkedAt", STAMP, nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("failures", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("problem", sa.String(length=300), nullable=True),
        sa.Column("archiveTriedAt", STAMP, nullable=True),
        sa.Column("archivedAt", STAMP, nullable=True),
        sa.Column("archiveUrl", sa.Text(), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", STAMP, server_default=sa.text("now()"), nullable=False),
        *_rules(),
    )
    op.create_index(op.f(f"{TABLE}_checkedAt_idx"), TABLE, ["checkedAt"])
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    op.drop_table(TABLE)


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _check(name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{TABLE}_{name}_check"))


def _rules() -> tuple[sa.Constraint, ...]:
    return (
        _check("outcome", f'"outcome" IN ({_listed(FETCH_OUTCOMES)})'),
        _check("failures", '"failures" >= 0'),
        _check("archived", '("archivedAt" IS NULL) = ("archiveUrl" IS NULL)'),
        _check("archive_tried", '"archivedAt" IS NULL OR "archiveTriedAt" IS NOT NULL'),
        sa.ForeignKeyConstraint(
            ["sourceId"], ["Source.id"], name=op.f(f"{TABLE}_sourceId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("sourceId", name=op.f(f"{TABLE}_pkey")),
    )
