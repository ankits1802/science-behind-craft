from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0043_embedding_stamps"
down_revision: str | Sequence[str] | None = "0042_page_layouts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODEL_CHARS = 120
HASH_CHARS = 64
TEXT_TABLES = ("Claim", "Chunk")
STAMP_TRIGGER = "embedding_stamp"
DESCRIPTOR_TRIGGER = "Craft_descriptor_stamp"

CURRENT_MODEL_FUNCTION = """
CREATE OR REPLACE FUNCTION kv_embedding_model() RETURNS text
LANGUAGE sql STABLE AS $fn$
    SELECT r.model
    FROM "RoutePolicy" r
    JOIN "Provider" p ON p.id = r."providerId"
    WHERE r.task = 'EMBED' AND r.enabled AND p.enabled
    ORDER BY r.ordinal
    LIMIT 1
$fn$
"""

STAMP_FUNCTION = """
CREATE OR REPLACE FUNCTION kv_stamp_embedding() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW."text" IS DISTINCT FROM OLD."text" AND NEW."embedding" IS NOT DISTINCT FROM OLD."embedding" THEN
            NEW."embedding" := NULL;
        END IF;
        IF NEW."embedding" IS NOT NULL AND NEW."embedding" IS DISTINCT FROM OLD."embedding"
            AND NEW."embeddingModel" IS NOT DISTINCT FROM OLD."embeddingModel" THEN
            NEW."embeddingModel" := kv_embedding_model();
        END IF;
    ELSIF NEW."embedding" IS NOT NULL AND NEW."embeddingModel" IS NULL THEN
        NEW."embeddingModel" := kv_embedding_model();
    END IF;
    IF NEW."embedding" IS NULL THEN
        NEW."embeddingModel" := NULL;
    END IF;
    RETURN NEW;
END;
$fn$
"""

DESCRIPTOR_FUNCTION = """
CREATE OR REPLACE FUNCTION kv_stamp_descriptor() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW."descriptorEmbedding" IS NOT NULL
            AND NEW."descriptorEmbedding" IS DISTINCT FROM OLD."descriptorEmbedding"
            AND NEW."embeddingModel" IS NOT DISTINCT FROM OLD."embeddingModel" THEN
            NEW."embeddingModel" := kv_embedding_model();
        END IF;
    ELSIF NEW."descriptorEmbedding" IS NOT NULL AND NEW."embeddingModel" IS NULL THEN
        NEW."embeddingModel" := kv_embedding_model();
    END IF;
    IF NEW."descriptorEmbedding" IS NULL THEN
        NEW."embeddingModel" := NULL;
        NEW."descriptorHash" := NULL;
    END IF;
    RETURN NEW;
END;
$fn$
"""


def _stamp_trigger(table: str) -> str:
    return f"""
CREATE TRIGGER "{table}_{STAMP_TRIGGER}"
BEFORE INSERT OR UPDATE OF "text", "embedding", "embeddingModel" ON "{table}"
FOR EACH ROW
EXECUTE FUNCTION kv_stamp_embedding()
"""


DESCRIPTOR_STAMP = f"""
CREATE TRIGGER "{DESCRIPTOR_TRIGGER}"
BEFORE INSERT OR UPDATE OF "descriptorEmbedding", "embeddingModel", "descriptorHash" ON "Craft"
FOR EACH ROW
EXECUTE FUNCTION kv_stamp_descriptor()
"""


def upgrade() -> None:
    op.add_column("Claim", sa.Column("embeddingModel", sa.String(length=MODEL_CHARS), nullable=True))
    op.add_column("Chunk", sa.Column("embeddingModel", sa.String(length=MODEL_CHARS), nullable=True))
    op.add_column("Craft", sa.Column("embeddingModel", sa.String(length=MODEL_CHARS), nullable=True))
    op.add_column("Craft", sa.Column("descriptorHash", sa.String(length=HASH_CHARS), nullable=True))
    op.execute(CURRENT_MODEL_FUNCTION)
    for table in TEXT_TABLES:
        op.execute(
            f'UPDATE "{table}" SET "embeddingModel" = kv_embedding_model() WHERE "embedding" IS NOT NULL'
        )
    op.execute(
        'UPDATE "Craft" SET "embeddingModel" = kv_embedding_model() WHERE "descriptorEmbedding" IS NOT NULL'
    )
    op.execute(STAMP_FUNCTION)
    op.execute(DESCRIPTOR_FUNCTION)
    for table in TEXT_TABLES:
        op.execute(_stamp_trigger(table))
    op.execute(DESCRIPTOR_STAMP)


def downgrade() -> None:
    op.execute(f'DROP TRIGGER IF EXISTS "{DESCRIPTOR_TRIGGER}" ON "Craft"')
    for table in TEXT_TABLES:
        op.execute(f'DROP TRIGGER IF EXISTS "{table}_{STAMP_TRIGGER}" ON "{table}"')
    op.execute("DROP FUNCTION IF EXISTS kv_stamp_descriptor()")
    op.execute("DROP FUNCTION IF EXISTS kv_stamp_embedding()")
    op.execute("DROP FUNCTION IF EXISTS kv_embedding_model()")
    op.drop_column("Craft", "descriptorHash")
    op.drop_column("Craft", "embeddingModel")
    op.drop_column("Chunk", "embeddingModel")
    op.drop_column("Claim", "embeddingModel")
