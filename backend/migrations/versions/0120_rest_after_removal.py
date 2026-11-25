from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0120_rest_after_removal"
down_revision: str | Sequence[str] | None = "0118_removed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAMP = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.add_column("StoredDocumentVersion", sa.Column("removedAt", STAMP, nullable=True))
    op.add_column("StoredDocument", sa.Column("refreshAskedAt", STAMP, nullable=True))


def downgrade() -> None:
    op.drop_column("StoredDocument", "refreshAskedAt")
    op.drop_column("StoredDocumentVersion", "removedAt")
