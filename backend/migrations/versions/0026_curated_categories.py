from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_curated_categories"
down_revision: str | Sequence[str] | None = "0025_signature_block_kinds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = ("CuratedCategory", "CuratedCategoryClaim")
COVERAGE_CLASSES = ("FULL", "THIN")
DISCIPLINES = (
    "OVERVIEW",
    "PROCESS",
    "CHEMISTRY",
    "PHYSICS",
    "MATERIALS",
    "GEOGRAPHY",
    "GEOLOGY",
    "CLIMATE",
    "ECOLOGY",
    "BOTANY",
    "HISTORY",
    "ECONOMICS",
    "DESIGN",
    "HEALTH",
)

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "{table}" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    _create_curated_categories()
    _create_curated_category_claims()
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))


def downgrade() -> None:
    for table in reversed(NEW_TABLES):
        op.drop_table(table)


def _create_curated_categories() -> None:
    op.create_table(
        "CuratedCategory",
        sa.Column("categoryId", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("curatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("coverage", sa.String(length=8), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("page", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("importedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"version" >= 1', name=op.f("CuratedCategory_version_check")),
        sa.CheckConstraint(
            f'"coverage" IN ({_listed(COVERAGE_CLASSES)})', name=op.f("CuratedCategory_coverage_check")
        ),
        sa.CheckConstraint("\"digest\" ~ '^[0-9a-f]{64}$'", name=op.f("CuratedCategory_digest_check")),
        sa.ForeignKeyConstraint(
            ["categoryId"],
            ["CraftCategory.id"],
            name=op.f("CuratedCategory_categoryId_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("categoryId", name=op.f("CuratedCategory_pkey")),
    )


def _create_curated_category_claims() -> None:
    op.create_table(
        "CuratedCategoryClaim",
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("categoryId", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=8), nullable=False),
        sa.Column("discipline", sa.String(length=16), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            f'"discipline" IN ({_listed(DISCIPLINES)})', name=op.f("CuratedCategoryClaim_discipline_check")
        ),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("CuratedCategoryClaim_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["categoryId"],
            ["CraftCategory.id"],
            name=op.f("CuratedCategoryClaim_categoryId_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("claimId", name=op.f("CuratedCategoryClaim_pkey")),
        sa.UniqueConstraint("categoryId", "key", name=op.f("CuratedCategoryClaim_categoryId_key_key")),
    )
