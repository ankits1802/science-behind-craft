from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0118_removed"
down_revision: str | Sequence[str] | None = "0117_sanganeri_parity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "StoredDocument"
COLUMN = "removedAt"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column(COLUMN, sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
