from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040_upload_links"
down_revision: str | Sequence[str] | None = "0039_upkeep"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "UploadLink"
STAMP = sa.DateTime(timezone=True)
INDEXED = (("userId", "expiresAt"), ("contributionId",))

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "UploadLink" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        "UploadLink",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("userTokenVersion", sa.Integer(), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("stageId", sa.UUID(), nullable=True),
        sa.Column("claimIds", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("linkHash", sa.String(length=64), nullable=False),
        sa.Column("slotHash", sa.String(length=64), nullable=True),
        sa.Column("declaration", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expiresAt", STAMP, nullable=False),
        sa.Column("usedAt", STAMP, nullable=True),
        sa.Column("contributionId", sa.UUID(), nullable=True),
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


def _check(name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{TABLE}_{name}_check"))


def _fk(column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"{TABLE}_{column}_fkey"), ondelete=ondelete
    )


def _rules() -> tuple[sa.Constraint, ...]:
    return (
        _check("slot_declared", '("slotHash" IS NULL) = ("declaration" IS NULL)'),
        _check("facts", 'cardinality("claimIds") >= 1'),
        _check("used", '"contributionId" IS NULL OR "usedAt" IS NOT NULL'),
        sa.UniqueConstraint("linkHash", name=op.f(f"{TABLE}_linkHash_key")),
        sa.UniqueConstraint("slotHash", name=op.f(f"{TABLE}_slotHash_key")),
        _fk("userId", "User", "CASCADE"),
        _fk("craftId", "Craft", "CASCADE"),
        _fk("stageId", "ProcessStage", "SET NULL"),
        _fk("contributionId", "ImageContribution", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
    )
