from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_explainer_versions_alerts"
down_revision: str | Sequence[str] | None = "0019_hidden_generated_explainers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = ("Notification", "AlertDigestSend")
NOTIFICATION_KINDS = ("ANSWER_IMPROVED",)
EXPLAINER_VERSION_CHECK = (
    '("explainerId" IS NULL AND "explainerVersion" IS NULL) OR '
    '("explainerVersion" >= 1 AND ("explainerVersion" = 1) = ("explainerId" = "id"))'
)
SAVED_ANSWER_CHECK = (
    '("answerId" IS NULL) = ("seenVersion" IS NULL) AND ("seenVersion" IS NULL OR "seenVersion" >= 1)'
)
FIRST_VERSIONS = (
    'UPDATE "Answer" SET "explainerId" = "id", "explainerVersion" = 1 '
    "WHERE \"payload\" -> 'explainer' IS NOT NULL"
)
ONE_SAVE_PER_ANSWER = (
    'DELETE FROM "SavedItem" later USING "SavedItem" earlier '
    'WHERE later."answerId" IS NOT NULL AND later."userId" = earlier."userId" '
    'AND later."answerId" = earlier."answerId" '
    'AND (later."createdAt", later."id") > (earlier."createdAt", earlier."id")'
)
SAVED_ANSWERS_SEEN = 'UPDATE "SavedItem" SET "seenVersion" = 1 WHERE "answerId" IS NOT NULL'

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "{table}" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    _version_answers()
    _keep_saved_answers()
    op.add_column(
        "UserPreference",
        sa.Column("alertDigest", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    _create_notifications()
    _create_digest_sends()
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))


def downgrade() -> None:
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
    op.drop_column("UserPreference", "alertDigest")
    op.drop_constraint(op.f("SavedItem_seenVersion_check"), "SavedItem", type_="check")
    op.drop_index("SavedItem_userId_answerId_key", table_name="SavedItem")
    op.drop_column("SavedItem", "checkedAt")
    op.drop_column("SavedItem", "seenVersion")
    op.drop_constraint(op.f("Answer_explainerVersion_check"), "Answer", type_="check")
    op.drop_constraint(op.f("Answer_explainerId_explainerVersion_key"), "Answer", type_="unique")
    op.drop_constraint(op.f("Answer_explainerId_fkey"), "Answer", type_="foreignkey")
    op.drop_column("Answer", "explainerVersion")
    op.drop_column("Answer", "explainerId")


def _version_answers() -> None:
    op.add_column("Answer", sa.Column("explainerId", sa.UUID(), nullable=True))
    op.add_column("Answer", sa.Column("explainerVersion", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("Answer_explainerId_fkey"), "Answer", "Answer", ["explainerId"], ["id"], ondelete="CASCADE"
    )
    op.execute(FIRST_VERSIONS)
    op.create_unique_constraint(
        op.f("Answer_explainerId_explainerVersion_key"), "Answer", ["explainerId", "explainerVersion"]
    )
    op.create_check_constraint(op.f("Answer_explainerVersion_check"), "Answer", EXPLAINER_VERSION_CHECK)


def _keep_saved_answers() -> None:
    op.add_column("SavedItem", sa.Column("seenVersion", sa.Integer(), nullable=True))
    op.add_column("SavedItem", sa.Column("checkedAt", sa.DateTime(timezone=True), nullable=True))
    op.execute(ONE_SAVE_PER_ANSWER)
    op.execute(SAVED_ANSWERS_SEEN)
    op.create_index(
        "SavedItem_userId_answerId_key",
        "SavedItem",
        ["userId", "answerId"],
        unique=True,
        postgresql_where=sa.text('"answerId" IS NOT NULL'),
    )
    op.create_check_constraint(op.f("SavedItem_seenVersion_check"), "SavedItem", SAVED_ANSWER_CHECK)


def _create_notifications() -> None:
    op.create_table(
        "Notification",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("explainerId", sa.UUID(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("readAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            f'"kind" IN ({_listed(NOTIFICATION_KINDS)})', name=op.f("Notification_kind_check")
        ),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("Notification_userId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["explainerId"], ["Answer.id"], name=op.f("Notification_explainerId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Notification_pkey")),
    )
    op.create_index(op.f("Notification_userId_createdAt_idx"), "Notification", ["userId", "createdAt"])
    op.create_index(op.f("Notification_explainerId_idx"), "Notification", ["explainerId"])
    op.create_index(
        "Notification_one_unread_key",
        "Notification",
        ["userId", "explainerId", "kind"],
        unique=True,
        postgresql_where=sa.text('"readAt" IS NULL'),
    )


def _create_digest_sends() -> None:
    op.create_table(
        "AlertDigestSend",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("weekOf", sa.Date(), nullable=False),
        sa.Column("items", sa.Integer(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"items" >= 1', name=op.f("AlertDigestSend_items_check")),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("AlertDigestSend_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("AlertDigestSend_pkey")),
        sa.UniqueConstraint("userId", "weekOf", name=op.f("AlertDigestSend_userId_weekOf_key")),
    )
