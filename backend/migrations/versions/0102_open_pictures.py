from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0102_open_pictures"
down_revision: str | Sequence[str] | None = "0101_oauth_code_token_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "OpenPicture"
CONTRIBUTIONS = "ImageContribution"
STAMP = sa.DateTime(timezone=True)
SITE_CHARS = 16
TITLE_CHARS = 300
AUTHOR_CHARS = 200
LICENCE_CHARS = 200
CREDIT_CHARS = 500
OPEN_LICENCE = "OPEN_LICENCE"
ORIGINS_BEFORE = ("PHOTOGRAPH", "DRAWING", "AI_GENERATED")
ORIGINS = (*ORIGINS_BEFORE, OPEN_LICENCE)
SITES = ("COMMONS", "OPENVERSE", "FLICKR")
REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "OpenPicture" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    _check_origins(ORIGINS)
    op.create_table(
        "OpenPicture",
        sa.Column("contributionId", sa.UUID(), nullable=False),
        sa.Column("site", sa.String(length=SITE_CHARS), nullable=False),
        sa.Column("pageUrl", sa.Text(), nullable=False),
        sa.Column("fileUrl", sa.Text(), nullable=False),
        sa.Column("recordUrl", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=TITLE_CHARS), nullable=False),
        sa.Column("author", sa.String(length=AUTHOR_CHARS), nullable=False),
        sa.Column("licence", sa.String(length=LICENCE_CHARS), nullable=False),
        sa.Column("licenceUrl", sa.Text(), nullable=True),
        sa.Column("credit", sa.String(length=CREDIT_CHARS), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("readAt", STAMP, nullable=False),
        sa.Column("createdAt", STAMP, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(_listed("site", SITES), name=op.f(f"{TABLE}_site_check")),
        sa.ForeignKeyConstraint(
            ["contributionId"],
            [f"{CONTRIBUTIONS}.id"],
            name=op.f(f"{TABLE}_contributionId_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("contributionId", name=op.f(f"{TABLE}_pkey")),
    )
    op.create_index(op.f(f"{TABLE}_pageUrl_idx"), TABLE, ["pageUrl"])
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    op.drop_table(TABLE)
    op.execute(f'DELETE FROM "{CONTRIBUTIONS}" WHERE "origin" = \'{OPEN_LICENCE}\'')
    _check_origins(ORIGINS_BEFORE)


def _check_origins(origins: Sequence[str]) -> None:
    name = op.f(f"{CONTRIBUTIONS}_origin_check")
    op.drop_constraint(name, CONTRIBUTIONS, type_="check")
    op.create_check_constraint(name, CONTRIBUTIONS, _listed("origin", origins))


def _listed(column: str, values: Sequence[str]) -> str:
    named = ", ".join(f"'{value}'" for value in values)
    return f'"{column}" IN ({named})'
