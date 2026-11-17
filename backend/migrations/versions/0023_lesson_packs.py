from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_lesson_packs"
down_revision: str | Sequence[str] | None = "0022_elevenlabs_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "LessonPack"
REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "LessonPack" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def upgrade() -> None:
    op.create_table(
        "LessonPack",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("explainerId", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"version" >= 1', name=op.f("LessonPack_version_check")),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("LessonPack_userId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["explainerId"], ["Answer.id"], name=op.f("LessonPack_explainerId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("LessonPack_pkey")),
    )
    op.create_index(op.f("LessonPack_userId_createdAt_idx"), TABLE, ["userId", "createdAt"])
    op.create_index(op.f("LessonPack_explainerId_idx"), TABLE, ["explainerId"])
    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)


def downgrade() -> None:
    op.drop_table(TABLE)
