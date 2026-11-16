from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_media_jobs"
down_revision: str | Sequence[str] | None = "0007_multilingual_answers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ASSET_FOREIGN_KEY = "MediaJob_assetId_fkey"
ASSET_INDEX = "MediaJob_assetId_idx"


def upgrade() -> None:
    op.add_column("MediaJob", sa.Column("assetId", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f(ASSET_FOREIGN_KEY), "MediaJob", "MediaAsset", ["assetId"], ["id"], ondelete="SET NULL"
    )
    op.create_index(op.f(ASSET_INDEX), "MediaJob", ["assetId"], unique=False)
    op.add_column("MediaAsset", sa.Column("model", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("MediaAsset", "model")
    op.drop_index(op.f(ASSET_INDEX), table_name="MediaJob")
    op.drop_constraint(op.f(ASSET_FOREIGN_KEY), "MediaJob", type_="foreignkey")
    op.drop_column("MediaJob", "assetId")
