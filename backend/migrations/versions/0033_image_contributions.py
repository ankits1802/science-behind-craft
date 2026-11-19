from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0033_image_contributions"
down_revision: str | Sequence[str] | None = "0032_knowledge_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "ImageContribution"
STAMP = sa.DateTime(timezone=True)
IMAGE_ORIGINS = ("PHOTOGRAPH", "DRAWING", "AI_GENERATED")
IMAGE_CONTRIBUTION_STATUSES = ("AWAITING_FILE", "PENDING", "APPROVED", "REJECTED", "WITHDRAWN")
INDEXED = (("status", "createdAt"), ("craftId",), ("contributorId",), ("assetId",), ("sha256",))

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "ImageContribution" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        "ImageContribution",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("contributorId", sa.UUID(), nullable=True),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("stageId", sa.UUID(), nullable=True),
        sa.Column(
            "claimIds", postgresql.ARRAY(sa.UUID()), server_default=sa.text("ARRAY[]::uuid[]"), nullable=False
        ),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("generator", sa.String(length=120), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("caption", sa.String(length=300), nullable=False),
        sa.Column("altText", sa.String(length=300), nullable=False),
        sa.Column("termsVersion", sa.String(length=40), nullable=False),
        sa.Column("rightsConfirmedAt", STAMP, nullable=False),
        sa.Column("status", sa.String(length=16), server_default="AWAITING_FILE", nullable=False),
        sa.Column("assetId", sa.UUID(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("aiMarked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("reviewedById", sa.UUID(), nullable=True),
        sa.Column("reviewedAt", STAMP, nullable=True),
        sa.Column("reviewNote", sa.String(length=500), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", STAMP, server_default=sa.text("now()"), nullable=False),
        *_rules(),
    )
    for columns in INDEXED:
        op.create_index(op.f(f"{TABLE}_{'_'.join(columns)}_idx"), TABLE, list(columns))
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    op.drop_table(TABLE)


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _check(name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{TABLE}_{name}_check"))


def _fk(column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"{TABLE}_{column}_fkey"), ondelete=ondelete
    )


def _rules() -> tuple[sa.Constraint, ...]:
    return (
        _check("origin", f'"origin" IN ({_listed(IMAGE_ORIGINS)})'),
        _check("status", f'"status" IN ({_listed(IMAGE_CONTRIBUTION_STATUSES)})'),
        _check(
            "ai_declared",
            '"origin" <> \'AI_GENERATED\' OR ("generator" IS NOT NULL AND "prompt" IS NOT NULL '
            'AND cardinality("claimIds") > 0)',
        ),
        _check("file", "NOT \"status\" IN ('PENDING', 'APPROVED') OR \"assetId\" IS NOT NULL"),
        _check("reviewed", "NOT \"status\" IN ('APPROVED', 'REJECTED') OR \"reviewedAt\" IS NOT NULL"),
        _fk("contributorId", "User", "SET NULL"),
        _fk("craftId", "Craft", "CASCADE"),
        _fk("stageId", "ProcessStage", "SET NULL"),
        _fk("assetId", "MediaAsset", "SET NULL"),
        _fk("reviewedById", "User", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
    )
