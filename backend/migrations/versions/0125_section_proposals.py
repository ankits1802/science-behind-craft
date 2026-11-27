from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0125_section_proposals"
down_revision: str | Sequence[str] | None = "0124_leftovers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "SectionProposal"
ITEMS = "StagedReviewItem"
SECTION_KIND = "SECTIONS"
STAMP = sa.DateTime(timezone=True)
FIELDS = (
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
    "SOCIETY",
    "POLICY",
)
STATUSES = ("PENDING", "APPROVED", "REJECTED", "REFUSED")
ORIGINS = ("CONTRIBUTION", "AGENT")
QUEUE_KINDS_BEFORE = (
    "FACTS",
    "COMPONENTS",
    "LAYOUTS",
    "STRUCTURE",
    "READINGS",
    "LAYERS",
    "STAGES",
    "PICTURE_CHECKS",
)
LATER_KINDS = ("SOURCES", "SOURCES_DIFFER", "IMAGES", "PAGES")
KINDS_BEFORE = (*QUEUE_KINDS_BEFORE, *LATER_KINDS)
KINDS = (*QUEUE_KINDS_BEFORE, SECTION_KIND, *LATER_KINDS)
INDEXED = ("proposerId", "craftId", "categoryId", "reviewedById", "sectionId")
REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "SectionProposal" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("proposerId", sa.UUID(), nullable=True),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("categoryId", sa.UUID(), nullable=True),
        sa.Column("field", sa.String(length=16), nullable=False),
        sa.Column("sentences", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("taskKey", sa.String(length=240), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column("reviewedById", sa.UUID(), nullable=True),
        sa.Column("reviewedAt", STAMP, nullable=True),
        sa.Column("reviewNote", sa.String(length=500), nullable=True),
        sa.Column("sectionId", sa.UUID(), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", STAMP, server_default=sa.text("now()"), nullable=False),
        *_rules(),
    )
    op.create_index(op.f(f"{TABLE}_status_createdAt_idx"), TABLE, ["status", "createdAt"])
    for column in INDEXED:
        op.create_index(op.f(f"{TABLE}_{column}_idx"), TABLE, [column])
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)
    _kind_check(KINDS)


def downgrade() -> None:
    op.execute(f'DELETE FROM "{ITEMS}" WHERE "kind" = \'{SECTION_KIND}\'')
    _kind_check(KINDS_BEFORE)
    op.drop_table(TABLE)


def _kind_check(kinds: Sequence[str]) -> None:
    name = op.f(f"{ITEMS}_kind_check")
    op.drop_constraint(name, ITEMS, type_="check")
    op.create_check_constraint(name, ITEMS, _listed("kind", kinds))


def _listed(column: str, values: Sequence[str]) -> str:
    named = ", ".join(f"'{value}'" for value in values)
    return f'"{column}" IN ({named})'


def _check(name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{TABLE}_{name}_check"))


def _fk(column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"{TABLE}_{column}_fkey"), ondelete=ondelete
    )


def _rules() -> tuple[sa.Constraint, ...]:
    return (
        _check("field", _listed("field", FIELDS)),
        _check("status", _listed("status", STATUSES)),
        _check("origin", _listed("origin", ORIGINS)),
        _check("sentences", 'jsonb_typeof("sentences") = \'array\' AND jsonb_array_length("sentences") > 0'),
        _check("checks", "jsonb_typeof(\"checks\") = 'array'"),
        _check("reviewed", "\"status\" IN ('PENDING', 'REFUSED') OR \"reviewedAt\" IS NOT NULL"),
        _check("subject", 'num_nonnulls("craftId", "categoryId") = 1'),
        _fk("proposerId", "User", "SET NULL"),
        _fk("craftId", "Craft", "CASCADE"),
        _fk("categoryId", "CraftCategory", "CASCADE"),
        _fk("reviewedById", "User", "SET NULL"),
        _fk("sectionId", "ArticleSection", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
    )
