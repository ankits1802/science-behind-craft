from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_share_links"
down_revision: str | Sequence[str] | None = "0029_unlimited_ai_use"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SHARED_TABLES: tuple[str, ...] = ("Answer", "LessonPack")
SHARE_TOKEN_CHARS = 64
SHARED_TOGETHER = '("shareToken" IS NULL) = ("sharedAt" IS NULL)'


def upgrade() -> None:
    op.add_column("Answer", sa.Column("shareToken", sa.String(SHARE_TOKEN_CHARS), nullable=True))
    op.add_column("Answer", sa.Column("sharedAt", sa.DateTime(timezone=True), nullable=True))
    op.add_column("LessonPack", sa.Column("shareToken", sa.String(SHARE_TOKEN_CHARS), nullable=True))
    op.add_column("LessonPack", sa.Column("sharedAt", sa.DateTime(timezone=True), nullable=True))
    for table in SHARED_TABLES:
        op.create_unique_constraint(op.f(f"{table}_shareToken_key"), table, ["shareToken"])
        op.create_check_constraint(op.f(f"{table}_shared_check"), table, SHARED_TOGETHER)


def downgrade() -> None:
    for table in SHARED_TABLES:
        op.drop_constraint(op.f(f"{table}_shared_check"), table, type_="check")
        op.drop_constraint(op.f(f"{table}_shareToken_key"), table, type_="unique")
    op.drop_column("LessonPack", "sharedAt")
    op.drop_column("LessonPack", "shareToken")
    op.drop_column("Answer", "sharedAt")
    op.drop_column("Answer", "shareToken")
