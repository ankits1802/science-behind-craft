from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0041_monograph_documents"
down_revision: str | Sequence[str] | None = "0040_upload_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "MonographDocument"
STAMP = sa.DateTime(timezone=True)

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "MonographDocument" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        "MonographDocument",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("subjectKind", sa.String(length=20), nullable=False),
        sa.Column("subjectSlug", sa.String(length=200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("contentHash", sa.String(length=64), nullable=False),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"version" >= 1', name=op.f(f"{TABLE}_version_check")),
        sa.UniqueConstraint(
            "subjectKind", "subjectSlug", "version", name=op.f(f"{TABLE}_subjectKind_subjectSlug_version_key")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
    )
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    op.drop_table(TABLE)
