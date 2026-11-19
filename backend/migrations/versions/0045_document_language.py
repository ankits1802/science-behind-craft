from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045_document_language"
down_revision: str | Sequence[str] | None = "0044_contributed_origin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "MonographDocument"
ENGLISH = "en"
OLD_KEY = f"{TABLE}_subjectKind_subjectSlug_version_key"
NEW_KEY = f"{TABLE}_subjectKind_subjectSlug_language_version_key"
LANGUAGE_IN_DOCUMENT = (
    f"""UPDATE "{TABLE}" SET "document" = "document" || jsonb_build_object('language', "language")"""
)
LANGUAGE_OUT_OF_DOCUMENT = f"""UPDATE "{TABLE}" SET "document" = "document" - 'language'"""
ONLY_ENGLISH_KEPT = f"""DELETE FROM "{TABLE}" WHERE "language" <> '{ENGLISH}'"""


def upgrade() -> None:
    op.add_column(
        "MonographDocument",
        sa.Column("language", sa.String(length=16), server_default=ENGLISH, nullable=False),
    )
    op.drop_constraint(op.f(OLD_KEY), TABLE, type_="unique")
    op.create_unique_constraint(op.f(NEW_KEY), TABLE, ["subjectKind", "subjectSlug", "language", "version"])
    op.execute(LANGUAGE_IN_DOCUMENT)


def downgrade() -> None:
    op.execute(ONLY_ENGLISH_KEPT)
    op.execute(LANGUAGE_OUT_OF_DOCUMENT)
    op.drop_constraint(op.f(NEW_KEY), TABLE, type_="unique")
    op.create_unique_constraint(op.f(OLD_KEY), TABLE, ["subjectKind", "subjectSlug", "version"])
    op.drop_column(TABLE, "language")
