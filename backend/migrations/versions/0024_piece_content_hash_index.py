from collections.abc import Sequence

from alembic import op

revision: str = "0024_piece_content_hash_index"
down_revision: str | Sequence[str] | None = "0023_lesson_packs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "KnowledgePiece"


def upgrade() -> None:
    op.create_index(op.f("KnowledgePiece_contentHash_idx"), TABLE, ["contentHash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("KnowledgePiece_contentHash_idx"), table_name=TABLE)
