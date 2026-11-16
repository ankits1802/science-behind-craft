from collections.abc import Sequence

from alembic import op

revision: str = "0002_portal_alias_source"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (("AliasSource", ("FR_SYNC",)),)

ALIAS_SOURCES_BEFORE = (
    "MASTER",
    "CROSS_PORTAL_CODE",
    "CURATED",
    "IMMERSIVE",
    "CXA",
    "DR_SYNC",
    "PROPOSED",
    "WIKIDATA",
    "TRANSLITERATION",
)


def upgrade() -> None:
    for enum_name, values in ENUM_ADDITIONS:
        for value in values:
            op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    op.execute("DELETE FROM \"CraftAlias\" WHERE source::text = 'FR_SYNC'")
    op.execute('ALTER TYPE "AliasSource" RENAME TO "AliasSource_before_0002"')
    listed = ", ".join(f"'{value}'" for value in ALIAS_SOURCES_BEFORE)
    op.execute(f'CREATE TYPE "AliasSource" AS ENUM ({listed})')
    op.execute(
        'ALTER TABLE "CraftAlias" ALTER COLUMN source TYPE "AliasSource" USING source::text::"AliasSource"'
    )
    op.execute('DROP TYPE "AliasSource_before_0002"')
