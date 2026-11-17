from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0015_knowledge_pieces"
down_revision: str | Sequence[str] | None = "0014_sectioned_answer_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "KnowledgePiece"
BLOCK_KINDS = (
    "prose",
    "process_ladder",
    "region_story",
    "map_layer",
    "reaction_player",
    "material_card",
    "molecule_3d",
    "images",
    "simulation",
    "what_if",
    "timeline_map",
    "zoom_story",
    "expert_view",
    "seasons",
    "supply_map",
    "compare",
    "in_practice",
    "quiz",
    "open_questions",
    "artisan_voice",
    "designs",
)
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
DEPTHS = ("BASIC", "DETAILED", "EXPERT")
HIDDEN_CLAIM_STATUSES = ("DRAFT", "REJECTED", "RETRACTED")


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


REVOKE_PUBLIC_ROLES = f"""
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "{TABLE}" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""

STALE_FUNCTION = """
CREATE OR REPLACE FUNCTION kv_stale_resting_pieces() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    UPDATE "KnowledgePiece"
    SET "staleSince" = now(), "updatedAt" = now()
    WHERE "claimIds" @> ARRAY[OLD.id] AND "staleSince" IS NULL;
    RETURN NULL;
END;
$fn$
"""

STALE_ON_CHANGE = f"""
CREATE TRIGGER "Claim_stales_resting_pieces"
AFTER UPDATE OF "status", "evidenceLevel", "text", "sensitivity" ON "Claim"
FOR EACH ROW
WHEN (
    (NEW."status" IS DISTINCT FROM OLD."status" AND NEW."status"::text IN ({_listed(HIDDEN_CLAIM_STATUSES)}))
    OR NEW."evidenceLevel" IS DISTINCT FROM OLD."evidenceLevel"
    OR NEW."text" IS DISTINCT FROM OLD."text"
    OR NEW."sensitivity" IS DISTINCT FROM OLD."sensitivity"
)
EXECUTE FUNCTION kv_stale_resting_pieces()
"""

STALE_ON_DELETE = """
CREATE TRIGGER "Claim_deleted_stales_resting_pieces"
AFTER DELETE ON "Claim"
FOR EACH ROW
EXECUTE FUNCTION kv_stale_resting_pieces()
"""


def upgrade() -> None:
    _create_pieces()
    _constrain_pieces()
    _index_pieces()
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)
    op.execute(STALE_FUNCTION)
    op.execute(STALE_ON_CHANGE)
    op.execute(STALE_ON_DELETE)


def downgrade() -> None:
    op.execute('DROP TRIGGER IF EXISTS "Claim_deleted_stales_resting_pieces" ON "Claim"')
    op.execute('DROP TRIGGER IF EXISTS "Claim_stales_resting_pieces" ON "Claim"')
    op.execute("DROP FUNCTION IF EXISTS kv_stale_resting_pieces()")
    op.drop_table(TABLE)


def _one_of(column: str, values: Sequence[str]) -> str:
    return f'"{column}" IN ({_listed(values)})'


def _create_pieces() -> None:
    op.create_table(
        "KnowledgePiece",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("facet", sa.String(length=16), nullable=False),
        sa.Column("topicKey", sa.String(length=200), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("depth", sa.String(length=16), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("claimIds", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.Column("sourceIds", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("contentHash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("createdFromAnswerId", sa.UUID(), nullable=True),
        sa.Column("staleSince", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersededById", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("KnowledgePiece_pkey")),
    )


def _constrain_pieces() -> None:
    for column, values in (("kind", BLOCK_KINDS), ("facet", DISCIPLINES), ("depth", DEPTHS)):
        op.create_check_constraint(op.f(f"KnowledgePiece_{column}_check"), TABLE, _one_of(column, values))
    op.create_check_constraint(
        op.f("KnowledgePiece_rests_on_check"),
        TABLE,
        'cardinality("claimIds") > 0 AND cardinality("sourceIds") > 0',
    )
    for column, target, ondelete in (
        ("craftId", "Craft", "CASCADE"),
        ("createdFromAnswerId", "Answer", "SET NULL"),
        ("supersededById", "KnowledgePiece", "SET NULL"),
    ):
        op.create_foreign_key(
            op.f(f"KnowledgePiece_{column}_fkey"), TABLE, target, [column], ["id"], ondelete=ondelete
        )


def _index_pieces() -> None:
    op.create_index(
        op.f("KnowledgePiece_craftId_facet_topicKey_idx"),
        TABLE,
        ["craftId", "facet", "topicKey"],
        unique=False,
    )
    op.create_index(
        "KnowledgePiece_claimIds_gin_idx", TABLE, ["claimIds"], unique=False, postgresql_using="gin"
    )
    for column in ("createdFromAnswerId", "supersededById"):
        op.create_index(op.f(f"KnowledgePiece_{column}_idx"), TABLE, [column], unique=False)
    op.create_index(
        op.f("KnowledgePiece_staleSince_idx"),
        TABLE,
        ["staleSince"],
        unique=False,
        postgresql_where=sa.text('"staleSince" IS NOT NULL'),
    )
