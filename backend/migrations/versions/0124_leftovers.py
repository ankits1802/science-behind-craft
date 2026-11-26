from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0124_leftovers"
down_revision: str | Sequence[str] | None = "0123_mcp_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "PageUpgrade"
HOLDS = "PageHold"
CRITIQUE = "critique"
SUBJECT_KIND_CHARS = 20
SLUG_CHARS = 200
SUBJECT_KINDS = ("craft", "family", "category")
REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "PageUpgrade" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.add_column("PageHold", sa.Column("critique", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_table(
        "PageUpgrade",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("subjectKind", sa.String(length=SUBJECT_KIND_CHARS), nullable=False),
        sa.Column("subjectSlug", sa.String(length=SLUG_CHARS), nullable=False),
        sa.Column("layoutVersion", sa.Integer(), nullable=False),
        sa.Column("lines", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raisedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(_listed("subjectKind", SUBJECT_KINDS), name=op.f(f"{TABLE}_subjectKind_check")),
        sa.CheckConstraint('"layoutVersion" >= 1', name=op.f(f"{TABLE}_layoutVersion_check")),
        sa.CheckConstraint("jsonb_typeof(\"lines\") = 'array'", name=op.f(f"{TABLE}_lines_check")),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
        sa.UniqueConstraint("subjectKind", "subjectSlug", name=op.f(f"{TABLE}_subjectKind_subjectSlug_key")),
    )
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    op.drop_table(TABLE)
    op.drop_column(HOLDS, CRITIQUE)


def _listed(column: str, values: Sequence[str]) -> str:
    named = ", ".join(f"'{value}'" for value in values)
    return f'"{column}" IN ({named})'
