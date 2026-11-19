from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0044_contributed_origin"
down_revision: str | Sequence[str] | None = "0043_embedding_stamps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "LayoutProposal"
STAMP = sa.DateTime(timezone=True)
CONTRIBUTED = "CONTRIBUTION"
RESEARCHER = "RESEARCHER"
ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (("ClaimOrigin", ("CONTRIBUTION",)),)
PROPOSED_FACTS = """
UPDATE "Claim" SET "origin" = '{to}'
WHERE "origin" = '{source}'
  AND "createdByKind" = 'USER'
  AND "predicate" = 'states'
  AND EXISTS (SELECT 1 FROM "CandidateCheck" WHERE "CandidateCheck"."claimId" = "Claim"."id")
"""

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "LayoutProposal" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for enum_name, values in ENUM_ADDITIONS:
            for value in values:
                op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")
    op.execute(PROPOSED_FACTS.format(to=CONTRIBUTED, source=RESEARCHER))
    _create_layout_proposals()


def downgrade() -> None:
    op.drop_table(TABLE)
    op.execute(PROPOSED_FACTS.format(to=RESEARCHER, source=CONTRIBUTED))


def _create_layout_proposals() -> None:
    op.create_table(
        "LayoutProposal",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("proposerId", sa.UUID(), nullable=True),
        sa.Column("subjectKind", sa.String(length=16), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("categoryId", sa.UUID(), nullable=True),
        sa.Column("baseVersion", sa.Integer(), nullable=False),
        sa.Column("entries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column("reviewedById", sa.UUID(), nullable=True),
        sa.Column("reviewedAt", STAMP, nullable=True),
        sa.Column("reviewNote", sa.String(length=500), nullable=True),
        sa.Column("layoutVersion", sa.Integer(), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", STAMP, server_default=sa.text("now()"), nullable=False),
        *_rules(),
    )
    op.create_index(op.f(f"{TABLE}_status_createdAt_idx"), TABLE, ["status", "createdAt"])
    for column in ("proposerId", "craftId", "categoryId", "reviewedById"):
        op.create_index(op.f(f"{TABLE}_{column}_idx"), TABLE, [column])
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def _check(name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{TABLE}_{name}_check"))


def _fk(column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"{TABLE}_{column}_fkey"), ondelete=ondelete
    )


def _rules() -> tuple[sa.Constraint, ...]:
    return (
        _check("status", "\"status\" IN ('PENDING', 'APPROVED', 'REJECTED')"),
        _check("origin", "\"origin\" IN ('CONTRIBUTION', 'AGENT')"),
        _check("subject_kind", "\"subjectKind\" IN ('craft', 'family', 'category')"),
        _check("one_subject", '("craftId" IS NULL) <> ("categoryId" IS NULL)'),
        _check("subject_matches_kind", '("subjectKind" = \'category\') = ("categoryId" IS NOT NULL)'),
        _check("base_version", '"baseVersion" >= 0'),
        _check("entries", "jsonb_typeof(\"entries\") = 'array'"),
        _check("reviewed", '"status" = \'PENDING\' OR "reviewedAt" IS NOT NULL'),
        _check("written", '("status" = \'APPROVED\') = ("layoutVersion" IS NOT NULL)'),
        _fk("proposerId", "User", "SET NULL"),
        _fk("craftId", "Craft", "CASCADE"),
        _fk("categoryId", "CraftCategory", "CASCADE"),
        _fk("reviewedById", "User", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
    )
