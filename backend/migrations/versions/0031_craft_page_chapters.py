from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0031_craft_page_chapters"
down_revision: str | Sequence[str] | None = "0030_share_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAMP = sa.DateTime(timezone=True)
VARIANTS = "\"variant\" IN ('OPEN', 'RESEARCHER')"
NEW_TABLES: tuple[str, ...] = ("CraftPageSnapshot", "CraftPageArchive", "WikidataPoint")

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


def upgrade() -> None:
    _page_tables()
    op.add_column("Compound", sa.Column("conformerKeptAt", STAMP, nullable=True))
    _wikidata_points()
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))


def _page_tables() -> None:
    op.create_table(
        "CraftPageSnapshot",
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("variant", sa.Text(), nullable=False),
        sa.Column("stamp", sa.Text(), nullable=False),
        sa.Column("schemaVersion", sa.Integer(), nullable=False),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("etag", sa.Text(), nullable=False),
        sa.Column("builtAt", STAMP, nullable=False),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("CraftPageSnapshot_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("craftId", "variant", name=op.f("CraftPageSnapshot_pkey")),
        sa.CheckConstraint(VARIANTS, name=op.f("CraftPageSnapshot_variant_check")),
    )
    op.create_table(
        "CraftPageArchive",
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("curationVersion", sa.Integer(), nullable=False),
        sa.Column("variant", sa.Text(), nullable=False),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("etag", sa.Text(), nullable=False),
        sa.Column("frozenAt", STAMP, nullable=False),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("CraftPageArchive_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("craftId", "curationVersion", "variant", name=op.f("CraftPageArchive_pkey")),
        sa.CheckConstraint(VARIANTS, name=op.f("CraftPageArchive_variant_check")),
    )


def _wikidata_points() -> None:
    op.create_table(
        "WikidataPoint",
        sa.Column("wikidataId", sa.String(length=20), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("keptAt", STAMP, nullable=False),
        sa.PrimaryKeyConstraint("wikidataId", name=op.f("WikidataPoint_pkey")),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",
            name=op.f("WikidataPoint_coordinates_check"),
        ),
    )


def downgrade() -> None:
    op.drop_table("WikidataPoint")
    op.drop_column("Compound", "conformerKeptAt")
    op.drop_table("CraftPageArchive")
    op.drop_table("CraftPageSnapshot")
