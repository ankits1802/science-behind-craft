from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_hidden_generated_explainers"
down_revision: str | Sequence[str] | None = "0018_learning_block_kinds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "KnowledgePiece"


def upgrade() -> None:
    op.add_column("KnowledgePiece", sa.Column("hiddenAt", sa.DateTime(timezone=True), nullable=True))
    op.add_column("KnowledgePiece", sa.Column("hiddenById", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("KnowledgePiece_hiddenById_fkey"), TABLE, "User", ["hiddenById"], ["id"], ondelete="SET NULL"
    )
    op.create_index(op.f("KnowledgePiece_hiddenById_idx"), TABLE, ["hiddenById"], unique=False)
    op.create_check_constraint(
        op.f("KnowledgePiece_hidden_by_check"), TABLE, '"hiddenById" IS NULL OR "hiddenAt" IS NOT NULL'
    )


def downgrade() -> None:
    op.drop_constraint(op.f("KnowledgePiece_hidden_by_check"), TABLE, type_="check")
    op.drop_index(op.f("KnowledgePiece_hiddenById_idx"), table_name=TABLE)
    op.drop_constraint(op.f("KnowledgePiece_hiddenById_fkey"), TABLE, type_="foreignkey")
    op.drop_column(TABLE, "hiddenById")
    op.drop_column(TABLE, "hiddenAt")
