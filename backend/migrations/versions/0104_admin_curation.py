from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0104_admin_curation"
down_revision: str | Sequence[str] | None = "0103_component_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ITEMS = "StagedReviewItem"
PICTURES = "ImageContribution"
ACTIONS_BEFORE = ("approve", "reject", "raise", "retract", "correct", "clear", "remove")
ACTIONS = (*ACTIONS_BEFORE, "edit")
KINDS_BEFORE = (
    "FACTS",
    "COMPONENTS",
    "LAYOUTS",
    "STRUCTURE",
    "READINGS",
    "LAYERS",
    "STAGES",
    "SOURCES",
    "SOURCES_DIFFER",
)
KINDS = (*KINDS_BEFORE, "IMAGES")
FOCAL_CHECK = f"{PICTURES}_focal_check"
FOCAL_OBJECT = '"focal" IS NULL OR jsonb_typeof("focal") = \'object\''


def upgrade() -> None:
    _listed_check("action", ACTIONS)
    _listed_check("kind", KINDS)
    op.add_column(
        "ImageContribution", sa.Column("focal", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.create_check_constraint(op.f(FOCAL_CHECK), PICTURES, FOCAL_OBJECT)


def downgrade() -> None:
    op.drop_constraint(op.f(FOCAL_CHECK), PICTURES, type_="check")
    op.drop_column("ImageContribution", "focal")
    op.execute(
        f'DELETE FROM "{ITEMS}" WHERE NOT ({_listed("action", ACTIONS_BEFORE)}) '
        f"OR NOT ({_listed('kind', KINDS_BEFORE)})"
    )
    _listed_check("kind", KINDS_BEFORE)
    _listed_check("action", ACTIONS_BEFORE)


def _listed_check(column: str, values: Sequence[str]) -> None:
    name = op.f(f"{ITEMS}_{column}_check")
    op.drop_constraint(name, ITEMS, type_="check")
    op.create_check_constraint(name, ITEMS, _listed(column, values))


def _listed(column: str, values: Sequence[str]) -> str:
    named = ", ".join(f"'{value}'" for value in values)
    return f'"{column}" IN ({named})'
