from collections.abc import Sequence

from alembic import op

revision: str = "0021_climate_trend_stats"
down_revision: str | Sequence[str] | None = "0020_explainer_versions_and_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("EnvStat", ("TREND_PER_DECADE", "TREND_P_VALUE")),
)

ENV_STATS_BEFORE = (
    "DISTRICT_MEAN",
    "DISTRICT_P10",
    "DISTRICT_P90",
    "UNCERTAINTY_Q05_MEAN",
    "UNCERTAINTY_Q95_MEAN",
    "SHARE",
    "CLASS",
    "NORMAL",
    "DISTRICT_MIN",
    "DISTRICT_MAX",
    "TOTAL",
    "DENSITY",
    "DISTANCE",
    "COUNT",
)
STAT_TABLE = "DistrictEnvValue"
STAT_COLUMN = "stat"


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for enum_name, values in ENUM_ADDITIONS:
            for value in values:
                op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    added = [value for _name, values in ENUM_ADDITIONS for value in values]
    op.execute(f'DELETE FROM "{STAT_TABLE}" WHERE "{STAT_COLUMN}"::text IN ({_listed(added)})')
    op.execute('ALTER TYPE "EnvStat" RENAME TO "EnvStat_before_0021"')
    op.execute(f'CREATE TYPE "EnvStat" AS ENUM ({_listed(ENV_STATS_BEFORE)})')
    op.execute(
        f'ALTER TABLE "{STAT_TABLE}" ALTER COLUMN "{STAT_COLUMN}" TYPE "EnvStat" '
        f'USING "{STAT_COLUMN}"::text::"EnvStat"'
    )
    op.execute('DROP TYPE "EnvStat_before_0021"')
