from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_region_profile"
down_revision: str | Sequence[str] | None = "0004_science_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LAYER_INDEX = "DistrictEnvValue_datasetId_variable_depthOrPeriod_stat_idx"
READ_GRIDS = (
    ("ESA_WORLDCOVER_2021_V200", "read at ([^;]+);"),
    ("COPERNICUS_DEM_GLO90", "area_spherical_km2 at ([^;]+);"),
)

GLIM_DATASET = "GLIM_1_0_05DEG"
GLIM_LEGEND = (
    ("su", "Unconsolidated sediments"),
    ("vb", "Basic volcanic rocks"),
    ("ss", "Siliciclastic sedimentary rocks"),
    ("pb", "Basic plutonic rocks"),
    ("sm", "Mixed sedimentary rocks"),
    ("sc", "Carbonate sedimentary rocks"),
    ("va", "Acid volcanic rocks"),
    ("mt", "Metamorphics"),
    ("pa", "Acid plutonic rocks"),
    ("vi", "Intermediate volcanic rocks"),
    ("wb", "Water bodies"),
    ("py", "Pyroclastics"),
    ("pi", "Intermediate plutonic rocks"),
    ("ev", "Evaporites"),
    ("nd", "No data"),
    ("ig", "Ice and glaciers"),
)


def upgrade() -> None:
    op.add_column("EnvDataset", sa.Column("url", sa.Text(), nullable=True))
    op.add_column("DistrictEnvValue", sa.Column("resolution", sa.String(length=120), nullable=True))
    op.add_column("DistrictGeology", sa.Column("lithologyName", sa.String(length=300), nullable=True))
    op.add_column("DistrictGeology", sa.Column("method", sa.Text(), nullable=True))
    op.create_index(
        op.f(LAYER_INDEX),
        "DistrictEnvValue",
        ["datasetId", "variable", "depthOrPeriod", "stat"],
        unique=False,
    )
    for statement in backfills():
        op.execute(statement)


def backfills() -> list[str]:
    grids = [
        'UPDATE "DistrictEnvValue" AS v '
        f"SET resolution = substring(v.method FROM '{pattern}') "
        'FROM "EnvDataset" AS d '
        f"WHERE d.id = v.\"datasetId\" AND d.code = '{code}' AND v.resolution IS NULL "
        f"AND v.method ~ '{pattern}'"
        for code, pattern in READ_GRIDS
    ]
    legend = ", ".join(f"('{code}', '{name}')" for code, name in GLIM_LEGEND)
    names = (
        'UPDATE "DistrictGeology" AS g SET "lithologyName" = legend.name '
        f'FROM (VALUES {legend}) AS legend(code, name), "EnvDataset" AS d '
        f"WHERE d.id = g.\"datasetId\" AND d.code = '{GLIM_DATASET}' "
        'AND g.lithology = legend.code AND g."lithologyName" IS NULL'
    )
    return [*grids, names]


def downgrade() -> None:
    op.drop_index(op.f(LAYER_INDEX), table_name="DistrictEnvValue")
    op.drop_column("DistrictGeology", "method")
    op.drop_column("DistrictGeology", "lithologyName")
    op.drop_column("DistrictEnvValue", "resolution")
    op.drop_column("EnvDataset", "url")
