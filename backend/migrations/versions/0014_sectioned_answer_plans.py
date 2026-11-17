from collections.abc import Sequence

from alembic import op

revision: str = "0014_sectioned_answer_plans"
down_revision: str | Sequence[str] | None = "0013_answer_understanding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE "Answer"
        SET plan = jsonb_build_object(
            'schemaVersion', 1,
            'sections', jsonb_build_array(
                jsonb_build_object('sectionId', 's1', 'discipline', 'OVERVIEW', 'plan', plan)
            )
        )
        WHERE plan IS NOT NULL AND plan -> 'sections' IS NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE "Answer"
        SET plan = plan -> 'sections' -> 0 -> 'plan'
        WHERE plan -> 'sections' IS NOT NULL
        """
    )
