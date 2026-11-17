from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0016_river_reaches"
down_revision: str | Sequence[str] | None = "0015_knowledge_pieces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("RiverBasin", "RiverReach")
STRAHLER_MAX = 15

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
    _create_basins()
    _create_reaches()
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))


def downgrade() -> None:
    op.drop_table("RiverReach")
    op.drop_table("RiverBasin")


def _create_basins() -> None:
    op.create_table(
        "RiverBasin",
        sa.Column("mainRiv", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("datasetId", sa.UUID(), nullable=False),
        sa.Column("reachCount", sa.Integer(), nullable=False),
        sa.Column("topologySha256", sa.String(length=64), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"reachCount" > 0', name=op.f("RiverBasin_reachCount_check")),
        sa.CheckConstraint(
            "\"topologySha256\" ~ '^[0-9a-f]{64}$'", name=op.f("RiverBasin_topologySha256_check")
        ),
        sa.ForeignKeyConstraint(
            ["datasetId"], ["EnvDataset.id"], name=op.f("RiverBasin_datasetId_fkey"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("mainRiv", name=op.f("RiverBasin_pkey")),
    )
    op.create_index(op.f("RiverBasin_datasetId_idx"), "RiverBasin", ["datasetId"], unique=False)


def _create_reaches() -> None:
    op.create_table(
        "RiverReach",
        sa.Column("hyrivId", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("nextDown", sa.Integer(), nullable=False),
        sa.Column("mainRiv", sa.Integer(), nullable=False),
        sa.Column("ordStra", sa.SmallInteger(), nullable=False),
        sa.Column("uplandSkm", sa.Float(), nullable=False),
        sa.Column("disAvCms", sa.Float(), nullable=False),
        sa.Column("lengthKm", sa.Float(), nullable=False),
        sa.Column(
            "geom", Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=False
        ),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            '"nextDown" >= 0 AND "nextDown" <> "hyrivId"', name=op.f("RiverReach_flows_on_check")
        ),
        sa.CheckConstraint(
            '("nextDown" = 0) = ("hyrivId" = "mainRiv")', name=op.f("RiverReach_outlet_check")
        ),
        sa.CheckConstraint(f'"ordStra" BETWEEN 1 AND {STRAHLER_MAX}', name=op.f("RiverReach_ordStra_check")),
        sa.CheckConstraint(
            '"uplandSkm" >= 0 AND "disAvCms" >= 0 AND "lengthKm" > 0', name=op.f("RiverReach_measures_check")
        ),
        sa.ForeignKeyConstraint(
            ["mainRiv"], ["RiverBasin.mainRiv"], name=op.f("RiverReach_mainRiv_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("hyrivId", name=op.f("RiverReach_pkey")),
    )
    op.create_index(op.f("RiverReach_mainRiv_idx"), "RiverReach", ["mainRiv"], unique=False)
    op.create_index(op.f("RiverReach_nextDown_idx"), "RiverReach", ["nextDown"], unique=False)
    op.create_index("RiverReach_geom_gist_idx", "RiverReach", ["geom"], unique=False, postgresql_using="gist")
