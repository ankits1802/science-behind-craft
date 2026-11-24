from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0103_component_lifecycle"
down_revision: str | Sequence[str] | None = "0101_oauth_code_token_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROPOSALS = "ComponentProposal"
UNLINKS = "KnowledgePieceUnlink"
HOLDS = "PageHold"
ITEMS = "StagedReviewItem"
STAMP = sa.DateTime(timezone=True)
LABEL_CHARS = 200
SUBJECT_KIND_CHARS = 16
SLUG_CHARS = 200
NAME_CHARS = 120
STATE_CHARS = 16
REASON_CHARS = 500
ACTIONS_BEFORE = ("approve", "reject", "raise", "retract", "correct", "clear")
ACTIONS = (*ACTIONS_BEFORE, "remove")
ACTION_CHECK = f"{ITEMS}_action_check"
HOLD_STATES = ("WAITING", "CONFIRMED", "DISCARDED")
HOLD_SUBJECTS = ("craft", "family", "category")
REPLACES_ANOTHER = (
    '"replacesLabel" IS NULL OR ("replacesLabel" <> "label" AND '
    "\"extension\" IS DISTINCT FROM 'SUBJECT_LINK')"
)
REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "KnowledgePieceUnlink" FROM %I', grantee);
            EXECUTE format('REVOKE ALL ON "PageHold" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.add_column(
        "ComponentProposal", sa.Column("replacesLabel", sa.String(length=LABEL_CHARS), nullable=True)
    )
    op.create_check_constraint(op.f(f"{PROPOSALS}_replaces_check"), PROPOSALS, REPLACES_ANOTHER)
    _unlinks()
    _holds()
    for table in (UNLINKS, HOLDS):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)
    _action_check(ACTIONS)


def downgrade() -> None:
    op.execute(f'DELETE FROM "{ITEMS}" WHERE NOT ({_listed("action", ACTIONS_BEFORE)})')
    _action_check(ACTIONS_BEFORE)
    op.drop_table(HOLDS)
    op.drop_table(UNLINKS)
    op.drop_constraint(op.f(f"{PROPOSALS}_replaces_check"), PROPOSALS, type_="check")
    op.drop_column("ComponentProposal", "replacesLabel")


def _unlinks() -> None:
    op.create_table(
        "KnowledgePieceUnlink",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pieceId", sa.UUID(), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("categoryId", sa.UUID(), nullable=True),
        sa.Column("unlinkedById", sa.UUID(), nullable=True),
        sa.Column("reason", sa.String(length=REASON_CHARS), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            '("craftId" IS NULL) <> ("categoryId" IS NULL)', name=op.f(f"{UNLINKS}_one_page_check")
        ),
        _fk(UNLINKS, "pieceId", "KnowledgePiece", "CASCADE"),
        _fk(UNLINKS, "craftId", "Craft", "CASCADE"),
        _fk(UNLINKS, "categoryId", "CraftCategory", "CASCADE"),
        _fk(UNLINKS, "unlinkedById", "User", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{UNLINKS}_pkey")),
    )
    for column in ("craftId", "categoryId"):
        op.create_index(
            f"{UNLINKS}_pieceId_{column}_key",
            UNLINKS,
            ["pieceId", column],
            unique=True,
            postgresql_where=sa.text(f'"{column}" IS NOT NULL'),
        )
    for column in ("craftId", "categoryId", "unlinkedById"):
        op.create_index(op.f(f"{UNLINKS}_{column}_idx"), UNLINKS, [column])


def _holds() -> None:
    op.create_table(
        "PageHold",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("subjectKind", sa.String(length=SUBJECT_KIND_CHARS), nullable=False),
        sa.Column("subjectSlug", sa.String(length=SLUG_CHARS), nullable=False),
        sa.Column("draftId", sa.UUID(), nullable=True),
        sa.Column("draftVersion", sa.Integer(), nullable=True),
        sa.Column("bundle", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("clientName", sa.String(length=NAME_CHARS), nullable=True),
        sa.Column("previewUrl", sa.Text(), nullable=True),
        sa.Column(
            "state", sa.String(length=STATE_CHARS), server_default=sa.text("'WAITING'"), nullable=False
        ),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("expiresAt", STAMP, nullable=False),
        sa.Column("decidedAt", STAMP, nullable=True),
        _check(HOLDS, "subjectKind", _listed("subjectKind", HOLD_SUBJECTS)),
        _check(HOLDS, "state", _listed("state", HOLD_STATES)),
        _check(HOLDS, "bundle", "jsonb_typeof(\"bundle\") = 'object'"),
        _check(HOLDS, "expires", '"expiresAt" > "createdAt"'),
        _check(HOLDS, "decided", '("state" = \'WAITING\') = ("decidedAt" IS NULL)'),
        _check(HOLDS, "confirmed", '("state" = \'CONFIRMED\') = ("result" IS NOT NULL)'),
        _fk(HOLDS, "userId", "User", "CASCADE"),
        _fk(HOLDS, "draftId", "PageDraft", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{HOLDS}_pkey")),
    )
    op.create_index(
        f"{HOLDS}_userId_subject_waiting_key",
        HOLDS,
        ["userId", "subjectKind", "subjectSlug"],
        unique=True,
        postgresql_where=sa.text("\"state\" = 'WAITING'"),
    )
    op.create_index(op.f(f"{HOLDS}_userId_createdAt_idx"), HOLDS, ["userId", "createdAt"])
    op.create_index(op.f(f"{HOLDS}_draftId_idx"), HOLDS, ["draftId"])


def _action_check(actions: Sequence[str]) -> None:
    op.drop_constraint(op.f(ACTION_CHECK), ITEMS, type_="check")
    op.create_check_constraint(op.f(ACTION_CHECK), ITEMS, _listed("action", actions))


def _check(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"{table}_{name}_check"))


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"{table}_{column}_fkey"), ondelete=ondelete
    )


def _listed(column: str, values: Sequence[str]) -> str:
    named = ", ".join(f"'{value}'" for value in values)
    return f'"{column}" IN ({named})'
