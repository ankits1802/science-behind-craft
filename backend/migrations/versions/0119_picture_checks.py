from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0119_picture_checks"
down_revision: str | Sequence[str] | None = "0118_removed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "PictureCheck"
LINKS = "MediaRefClaim"
ITEMS = "StagedReviewItem"
STAMP = sa.DateTime(timezone=True)
VERDICT_CHARS = 16
REASON_CHARS = 300
REASON_MIN_CHARS = 12
VERDICTS = ("SHOWS", "DOES_NOT_SHOW")
CHECKED_KIND = "PICTURE_CHECKS"
KINDS_BEFORE = (
    "FACTS",
    "COMPONENTS",
    "LAYOUTS",
    "STRUCTURE",
    "READINGS",
    "LAYERS",
    "STAGES",
    "SOURCES",
    "SOURCES_DIFFER",
    "IMAGES",
)
KINDS = (*KINDS_BEFORE[:7], CHECKED_KIND, *KINDS_BEFORE[7:])
REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "PictureCheck" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.add_column(
        "MediaRefClaim",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
    )
    op.add_column("MediaRefClaim", sa.Column("refusedAt", STAMP, nullable=True))
    op.create_unique_constraint(op.f(f"{LINKS}_id_key"), LINKS, ["id"])
    _create_checks()
    _listed_check("kind", KINDS)


def downgrade() -> None:
    op.execute(f'DELETE FROM "{ITEMS}" WHERE "kind" = \'{CHECKED_KIND}\'')
    _listed_check("kind", KINDS_BEFORE)
    op.drop_table(TABLE)
    op.drop_constraint(op.f(f"{LINKS}_id_key"), LINKS, type_="unique")
    op.drop_column("MediaRefClaim", "refusedAt")
    op.drop_column("MediaRefClaim", "id")


def _create_checks() -> None:
    op.create_table(
        "PictureCheck",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("linkId", sa.UUID(), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=True),
        sa.Column("verdict", sa.String(length=VERDICT_CHARS), nullable=False),
        sa.Column("reason", sa.String(length=REASON_CHARS), nullable=True),
        sa.Column("ruling", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("trusted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(_listed("verdict", VERDICTS), name=op.f(f"{TABLE}_verdict_check")),
        sa.CheckConstraint(
            f'"ruling" OR char_length("reason") BETWEEN {REASON_MIN_CHARS} AND {REASON_CHARS}',
            name=op.f(f"{TABLE}_reason_check"),
        ),
        sa.ForeignKeyConstraint(
            ["linkId"], [f"{LINKS}.id"], name=op.f(f"{TABLE}_linkId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f(f"{TABLE}_userId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"{TABLE}_pkey")),
    )
    op.create_index(
        f"{TABLE}_linkId_userId_once_key",
        TABLE,
        ["linkId", "userId"],
        unique=True,
        postgresql_where=sa.text('NOT "ruling"'),
    )
    op.create_index(op.f(f"{TABLE}_linkId_createdAt_idx"), TABLE, ["linkId", "createdAt"])
    op.create_index(op.f(f"{TABLE}_userId_createdAt_idx"), TABLE, ["userId", "createdAt"])
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def _listed_check(column: str, values: Sequence[str]) -> None:
    name = op.f(f"{ITEMS}_{column}_check")
    op.drop_constraint(name, ITEMS, type_="check")
    op.create_check_constraint(name, ITEMS, _listed(column, values))


def _listed(column: str, values: Sequence[str]) -> str:
    named = ", ".join(f"'{value}'" for value in values)
    return f'"{column}" IN ({named})'
