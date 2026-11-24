from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0108_render_review"
down_revision: str | Sequence[str] | None = "0103_component_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PREVIEWS = "PagePreview"
DRAWING_CHARS = 16
DRAWINGS = ("CHECKED", "FAILED", "UNMADE")
DRAWING_CHECK = '"drawing" IN (' + ", ".join(f"'{value}'" for value in DRAWINGS) + ")"


def upgrade() -> None:
    op.add_column("PagePreview", sa.Column("drawing", sa.String(length=DRAWING_CHARS), nullable=True))
    op.add_column(
        "PagePreview", sa.Column("drawingProblems", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.create_check_constraint(op.f(f"{PREVIEWS}_drawing_check"), PREVIEWS, DRAWING_CHECK)


def downgrade() -> None:
    op.drop_constraint(op.f(f"{PREVIEWS}_drawing_check"), PREVIEWS, type_="check")
    op.drop_column("PagePreview", "drawingProblems")
    op.drop_column("PagePreview", "drawing")
