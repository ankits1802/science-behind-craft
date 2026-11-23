from collections.abc import Sequence

from alembic import op

revision: str = "0100_signed_in_chunks_public"
down_revision: str | Sequence[str] | None = "0099_craft_group_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "Chunk"
PUBLIC = "PUBLIC"
SIGNED_IN = "SIGNED_IN"
WINDOW = "WINDOW"
MARK_TRIGGER = "Chunk_kind_window_mark"
MARK_FUNCTION_NAME = "kv_mark_window_chunk"
FOLD_INTO_PUBLIC = f"""UPDATE "{TABLE}" SET "acl" = '{PUBLIC}' WHERE "acl" = '{SIGNED_IN}'"""
MARK_FUNCTION = f"""
CREATE OR REPLACE FUNCTION {MARK_FUNCTION_NAME}() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF NEW."acl" = '{SIGNED_IN}' THEN
        NEW."kind" := '{WINDOW}';
    END IF;
    RETURN NEW;
END
$fn$
"""
CREATE_TRIGGER = f"""
CREATE TRIGGER "{MARK_TRIGGER}"
BEFORE INSERT ON "{TABLE}"
FOR EACH ROW EXECUTE FUNCTION {MARK_FUNCTION_NAME}()
"""


def upgrade() -> None:
    op.execute(FOLD_INTO_PUBLIC)
    op.execute(f'DROP TRIGGER IF EXISTS "{MARK_TRIGGER}" ON "{TABLE}"')
    op.execute(f"DROP FUNCTION IF EXISTS {MARK_FUNCTION_NAME}()")


def downgrade() -> None:
    op.execute(MARK_FUNCTION)
    op.execute(CREATE_TRIGGER)
