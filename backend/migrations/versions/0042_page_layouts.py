from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0042_page_layouts"
down_revision: str | Sequence[str] | None = "0041_monograph_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "PageLayout"
STAMP = sa.DateTime(timezone=True)
SUBJECT_COLUMNS = ("craftId", "categoryId")

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "PageLayout" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        "PageLayout",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("categoryId", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("entries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "writtenByKind",
            postgresql.ENUM("USER", "SYSTEM", name="ActorKind", create_type=False),
            server_default="SYSTEM",
            nullable=False,
        ),
        sa.Column("writtenById", sa.UUID(), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        *_rules(),
    )
    for column in SUBJECT_COLUMNS:
        op.create_index(
            f"{TABLE}_{column}_version_key",
            TABLE,
            [column, "version"],
            unique=True,
            postgresql_where=sa.text(f'"{column}" IS NOT NULL'),
        )
    op.create_index(op.f(f"{TABLE}_writtenById_idx"), TABLE, ["writtenById"])
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
        _check("version", '"version" >= 1'),
        _check("one_subject", '("craftId" IS NULL) <> ("categoryId" IS NULL)'),
        _check("entries", "jsonb_typeof(\"entries\") = 'array'"),
        _fk("craftId", "Craft", "CASCADE"),
        _fk("categoryId", "CraftCategory", "CASCADE"),
        _fk("writtenById", "User", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
    )
