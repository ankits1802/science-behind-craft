from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_curated_dossiers"
down_revision: str | Sequence[str] | None = "0016_river_reaches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (("ClaimStatus", ("SUPERSEDED", "WITHDRAWN")),)

CLAIM_STATUSES_BEFORE = ("DRAFT", "PROPOSED", "IN_REVIEW", "APPROVED", "REJECTED", "RETRACTED")
HIDDEN_BEFORE = ("DRAFT", "REJECTED", "RETRACTED")
HIDDEN_CLAIM_STATUSES = (*HIDDEN_BEFORE, "SUPERSEDED", "WITHDRAWN")
DOWNGRADED_TO = "RETRACTED"

CLAIM_STATUS_COLUMNS: tuple[tuple[str, str, str | None], ...] = (
    ("Claim", "status", "APPROVED"),
    ("ReviewEvent", "fromStatus", None),
    ("ReviewEvent", "toStatus", None),
)

NEW_TABLES = ("CuratedCraft", "CuratedClaim", "CraftGiRecord", "CraftPrice", "CraftWorkforce")
PARTIAL_DATE_CHECK = "~ '^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$'"
COVERAGE_CLASSES = ("FULL", "THIN")
DISCIPLINES = (
    "OVERVIEW",
    "PROCESS",
    "CHEMISTRY",
    "PHYSICS",
    "MATERIALS",
    "GEOGRAPHY",
    "GEOLOGY",
    "CLIMATE",
    "ECOLOGY",
    "BOTANY",
    "HISTORY",
    "ECONOMICS",
    "DESIGN",
    "HEALTH",
)
PLACE_ROLES = (
    "PRACTISED",
    "ORIGIN",
    "HISTORIC_CENTRE",
    "MATERIAL_SOURCE",
    "MARKET",
    "MIGRATED_FROM",
    "MIGRATED_TO",
)

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

STALE_TRIGGER = "Claim_stales_resting_pieces"


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _stale_on_change(hidden: Sequence[str]) -> str:
    return f"""
CREATE TRIGGER "{STALE_TRIGGER}"
AFTER UPDATE OF "status", "evidenceLevel", "text", "sensitivity" ON "Claim"
FOR EACH ROW
WHEN (
    (NEW."status" IS DISTINCT FROM OLD."status" AND NEW."status"::text IN ({_listed(hidden)}))
    OR NEW."evidenceLevel" IS DISTINCT FROM OLD."evidenceLevel"
    OR NEW."text" IS DISTINCT FROM OLD."text"
    OR NEW."sensitivity" IS DISTINCT FROM OLD."sensitivity"
)
EXECUTE FUNCTION kv_stale_resting_pieces()
"""


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for enum_name, values in ENUM_ADDITIONS:
            for value in values:
                op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")
    op.execute(f'DROP TRIGGER IF EXISTS "{STALE_TRIGGER}" ON "Claim"')
    op.execute(_stale_on_change(HIDDEN_CLAIM_STATUSES))
    _create_curated_crafts()
    _create_curated_claims()
    _create_gi_records()
    _create_prices()
    _create_workforce()
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))
    op.add_column("CraftLocation", sa.Column("role", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        op.f("CraftLocation_role_check"), "CraftLocation", f'"role" IN ({_listed(PLACE_ROLES)})'
    )
    op.add_column(
        "ProcessStage", sa.Column("ordered", sa.Boolean(), server_default=sa.text("true"), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("ProcessStage", "ordered")
    op.drop_constraint(op.f("CraftLocation_role_check"), "CraftLocation", type_="check")
    op.drop_column("CraftLocation", "role")
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
    op.execute(f'DROP TRIGGER IF EXISTS "{STALE_TRIGGER}" ON "Claim"')
    _restore_claim_statuses()
    op.execute(_stale_on_change(HIDDEN_BEFORE))


def _restore_claim_statuses() -> None:
    added = {value for _name, values in ENUM_ADDITIONS for value in values}
    op.execute('ALTER TYPE "ClaimStatus" RENAME TO "ClaimStatus_before_0017"')
    op.execute(f'CREATE TYPE "ClaimStatus" AS ENUM ({_listed(CLAIM_STATUSES_BEFORE)})')
    for table, column, default in CLAIM_STATUS_COLUMNS:
        if default is not None:
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP DEFAULT')
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE "ClaimStatus" USING '
            f"(CASE WHEN \"{column}\"::text IN ({_listed(sorted(added))}) THEN '{DOWNGRADED_TO}' "
            f'ELSE "{column}"::text END)::"ClaimStatus"'
        )
        if default is not None:
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT \'{default}\'')
    op.execute('DROP TYPE "ClaimStatus_before_0017"')


def _create_curated_crafts() -> None:
    op.create_table(
        "CuratedCraft",
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("curatedAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("coverage", sa.String(length=8), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("page", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("importedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"version" >= 1', name=op.f("CuratedCraft_version_check")),
        sa.CheckConstraint(
            f'"coverage" IN ({_listed(COVERAGE_CLASSES)})', name=op.f("CuratedCraft_coverage_check")
        ),
        sa.CheckConstraint("\"digest\" ~ '^[0-9a-f]{64}$'", name=op.f("CuratedCraft_digest_check")),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("CuratedCraft_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("craftId", name=op.f("CuratedCraft_pkey")),
    )


def _create_curated_claims() -> None:
    op.create_table(
        "CuratedClaim",
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=8), nullable=False),
        sa.Column("discipline", sa.String(length=16), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            f'"discipline" IN ({_listed(DISCIPLINES)})', name=op.f("CuratedClaim_discipline_check")
        ),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("CuratedClaim_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("CuratedClaim_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("claimId", name=op.f("CuratedClaim_pkey")),
        sa.UniqueConstraint("craftId", "key", name=op.f("CuratedClaim_craftId_key_key")),
    )


def _create_gi_records() -> None:
    op.create_table(
        "CraftGiRecord",
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("applicationNumber", sa.String(length=40), nullable=True),
        sa.Column("certificateNumber", sa.String(length=40), nullable=True),
        sa.Column("filedOn", sa.String(length=10), nullable=True),
        sa.Column("registeredOn", sa.String(length=10), nullable=True),
        sa.Column("journalIssue", sa.String(length=100), nullable=True),
        sa.Column(
            "proprietors",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("ARRAY[]::text[]"),
            nullable=False,
        ),
        sa.Column("authorisedUserCount", sa.Integer(), nullable=True),
        sa.Column("claimIds", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f'"filedOn" {PARTIAL_DATE_CHECK}', name=op.f("CraftGiRecord_filedOn_check")),
        sa.CheckConstraint(
            f'"registeredOn" {PARTIAL_DATE_CHECK}', name=op.f("CraftGiRecord_registeredOn_check")
        ),
        sa.CheckConstraint(
            '"authorisedUserCount" >= 0', name=op.f("CraftGiRecord_authorisedUserCount_check")
        ),
        sa.CheckConstraint('cardinality("claimIds") > 0', name=op.f("CraftGiRecord_claimIds_check")),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("CraftGiRecord_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("craftId", name=op.f("CraftGiRecord_pkey")),
    )


def _create_prices() -> None:
    op.create_table(
        "CraftPrice",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("pricedOn", sa.String(length=10), nullable=False),
        sa.Column("placeName", sa.String(length=300), nullable=False),
        sa.Column("stateLgd", sa.Integer(), nullable=True),
        sa.Column("districtLgd", sa.Integer(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f'"pricedOn" {PARTIAL_DATE_CHECK}', name=op.f("CraftPrice_pricedOn_check")),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("CraftPrice_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("CraftPrice_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["stateLgd"], ["AdminState.lgd"], name=op.f("CraftPrice_stateLgd_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["districtLgd"],
            ["AdminDistrict.lgd"],
            name=op.f("CraftPrice_districtLgd_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("CraftPrice_pkey")),
    )
    op.create_index(op.f("CraftPrice_craftId_idx"), "CraftPrice", ["craftId"], unique=False)
    op.create_index(op.f("CraftPrice_claimId_idx"), "CraftPrice", ["claimId"], unique=False)


def _create_workforce() -> None:
    op.create_table(
        "CraftWorkforce",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"year" BETWEEN 1000 AND 2100', name=op.f("CraftWorkforce_year_check")),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("CraftWorkforce_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("CraftWorkforce_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("CraftWorkforce_pkey")),
    )
    op.create_index(op.f("CraftWorkforce_craftId_idx"), "CraftWorkforce", ["craftId"], unique=False)
    op.create_index(op.f("CraftWorkforce_claimId_idx"), "CraftWorkforce", ["claimId"], unique=False)
