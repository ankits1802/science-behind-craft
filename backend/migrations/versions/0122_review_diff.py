from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0122_review_diff"
down_revision: str | Sequence[str] | None = "0121_coded_figures"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ITEMS = "StagedReviewItem"
PAGE_KIND = "PAGES"
KINDS_BEFORE = (
    "FACTS",
    "COMPONENTS",
    "LAYOUTS",
    "STRUCTURE",
    "READINGS",
    "LAYERS",
    "STAGES",
    "PICTURE_CHECKS",
    "SOURCES",
    "SOURCES_DIFFER",
    "IMAGES",
)
KINDS = (*KINDS_BEFORE, PAGE_KIND)
PROPOSALS = "PageProposal"
PICTURES = "DrawnPicture"
TABLES = (PROPOSALS, PICTURES)
STAMP = sa.DateTime(timezone=True)
SUBJECT_KIND_CHARS = 16
SLUG_CHARS = 200
ORIGIN_CHARS = 16
SIDE_CHARS = 8
PICTURE_NAME_CHARS = 80
SUBJECT_KINDS = ("craft", "family", "category")
SIDES = ("BEFORE", "AFTER")
REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "PageProposal" FROM %I', grantee);
            EXECUTE format('REVOKE ALL ON "DrawnPicture" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    _proposals()
    _pictures()
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)
    _kind_check(KINDS)


def downgrade() -> None:
    op.execute(f'DELETE FROM "{ITEMS}" WHERE "kind" = \'{PAGE_KIND}\'')
    _kind_check(KINDS_BEFORE)
    op.drop_table(PICTURES)
    op.drop_table(PROPOSALS)


def _kind_check(kinds: Sequence[str]) -> None:
    name = op.f(f"{ITEMS}_kind_check")
    op.drop_constraint(name, ITEMS, type_="check")
    op.create_check_constraint(name, ITEMS, _listed("kind", kinds))


def _proposals() -> None:
    op.create_table(
        "PageProposal",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("subjectKind", sa.String(length=SUBJECT_KIND_CHARS), nullable=False),
        sa.Column("subjectSlug", sa.String(length=SLUG_CHARS), nullable=False),
        sa.Column("origin", sa.String(length=ORIGIN_CHARS), nullable=False),
        sa.Column("parts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "decisions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("closedAt", STAMP, nullable=True),
        _check(PROPOSALS, "subjectKind", _listed("subjectKind", SUBJECT_KINDS)),
        _check(PROPOSALS, "parts", "jsonb_typeof(\"parts\") = 'array'"),
        _check(PROPOSALS, "changes", "jsonb_typeof(\"changes\") = 'array'"),
        _check(PROPOSALS, "decisions", "jsonb_typeof(\"decisions\") = 'array'"),
        _fk(PROPOSALS, "userId", "User"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{PROPOSALS}_pkey")),
    )
    op.create_index(op.f(f"{PROPOSALS}_userId_createdAt_idx"), PROPOSALS, ["userId", "createdAt"])
    op.create_index(op.f(f"{PROPOSALS}_closedAt_createdAt_idx"), PROPOSALS, ["closedAt", "createdAt"])


def _pictures() -> None:
    op.create_table(
        "DrawnPicture",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("previewId", sa.UUID(), nullable=True),
        sa.Column("proposalId", sa.UUID(), nullable=True),
        sa.Column("side", sa.String(length=SIDE_CHARS), nullable=False),
        sa.Column("name", sa.String(length=PICTURE_NAME_CHARS), nullable=False),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        _check(PICTURES, "one_owner", '("previewId" IS NULL) <> ("proposalId" IS NULL)'),
        _check(PICTURES, "side", _listed("side", SIDES)),
        _check(PICTURES, "size", '"width" >= 1 AND "height" >= 1'),
        _fk(PICTURES, "previewId", "PagePreview"),
        _fk(PICTURES, "proposalId", PROPOSALS),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{PICTURES}_pkey")),
    )
    op.create_index(op.f(f"{PICTURES}_previewId_idx"), PICTURES, ["previewId"])
    op.create_index(op.f(f"{PICTURES}_proposalId_side_idx"), PICTURES, ["proposalId", "side"])


def _check(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{table}_{name}_check"))


def _fk(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"{table}_{column}_fkey"), ondelete="CASCADE"
    )


def _listed(column: str, values: Sequence[str]) -> str:
    named = ", ".join(f"'{value}'" for value in values)
    return f'"{column}" IN ({named})'
