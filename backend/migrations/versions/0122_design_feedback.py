from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0122_design_feedback"
down_revision: str | Sequence[str] | None = "0121_coded_figures"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "DesignReadCache"
KEY_CHARS = 64
PROVIDER_CHARS = 64
MODEL_CHARS = 120
REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "DesignReadCache" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        "DesignReadCache",
        sa.Column("picturesKey", sa.String(length=KEY_CHARS), nullable=False),
        sa.Column("reading", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider", sa.String(length=PROVIDER_CHARS), nullable=False),
        sa.Column("model", sa.String(length=MODEL_CHARS), nullable=False),
        sa.Column("costUsd", sa.Numeric(precision=12, scale=6), server_default=sa.text("0"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            f'char_length("picturesKey") = {KEY_CHARS}', name=op.f(f"{TABLE}_picturesKey_check")
        ),
        sa.CheckConstraint("jsonb_typeof(\"reading\") = 'object'", name=op.f(f"{TABLE}_reading_check")),
        sa.CheckConstraint('"costUsd" >= 0', name=op.f(f"{TABLE}_cost_check")),
        sa.PrimaryKeyConstraint("picturesKey", name=op.f(f"{TABLE}_pkey")),
    )
    op.create_index(op.f(f"{TABLE}_createdAt_idx"), TABLE, ["createdAt"])
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)
    op.add_column(
        "PagePreview", sa.Column("critique", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        "LayoutProposal", sa.Column("critique", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("LayoutProposal", "critique")
    op.drop_column("PagePreview", "critique")
    op.drop_table(TABLE)
