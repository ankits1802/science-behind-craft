from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_claim_source_provenance"
down_revision: str | Sequence[str] | None = "0002_portal_alias_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ClaimSource", sa.Column("foundBy", sa.String(length=20), nullable=True))
    op.add_column("ClaimSource", sa.Column("answerId", sa.UUID(), nullable=True))
    op.add_column("ClaimSource", sa.Column("retrievedAt", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        op.f("ClaimSource_answerId_fkey"), "ClaimSource", "Answer", ["answerId"], ["id"], ondelete="SET NULL"
    )
    op.create_index(op.f("ClaimSource_answerId_idx"), "ClaimSource", ["answerId"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ClaimSource_answerId_idx"), table_name="ClaimSource")
    op.drop_constraint(op.f("ClaimSource_answerId_fkey"), "ClaimSource", type_="foreignkey")
    op.drop_column("ClaimSource", "retrievedAt")
    op.drop_column("ClaimSource", "answerId")
    op.drop_column("ClaimSource", "foundBy")
