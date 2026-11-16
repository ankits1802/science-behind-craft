from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_multilingual_answers"
down_revision: str | Sequence[str] | None = "0006_voice_session_binding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRANSLATE_OUTPUT_TOKENS = 8192
TRANSLATE_ROUTES: list[dict] = [
    {"ordinal": 1, "provider": "GEMINI", "model": "gemini-3.8-flash"},
    {"ordinal": 2, "provider": "ANTHROPIC", "model": "claude-sonnet-5-5"},
    {"ordinal": 3, "provider": "OPENAI", "model": "gpt-6.1-terra"},
]

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON "ClaimTranslation" FROM %I', grantee);
        END IF;
    END LOOP;
END
$do$
"""

INSERT_ROUTE = (
    'INSERT INTO "RoutePolicy" (task, ordinal, "providerId", model, "maxOutputTokens") '
    'SELECT CAST(\'TRANSLATE\' AS "AiTask"), :ordinal, p.id, :model, :tokens FROM "Provider" p '
    'WHERE p.name = CAST(:provider AS "AiProvider") '
    "ON CONFLICT (task, ordinal) DO NOTHING"
)


def upgrade() -> None:
    _create_claim_translation()
    op.execute('ALTER TABLE "ClaimTranslation" ENABLE ROW LEVEL SECURITY')
    op.execute(REVOKE_PUBLIC_ROLES)
    op.add_column(
        "UserPreference",
        sa.Column("answerLanguage", sa.String(length=16), server_default="auto", nullable=False),
    )
    for route in TRANSLATE_ROUTES:
        op.execute(sa.text(INSERT_ROUTE).bindparams(**route, tokens=TRANSLATE_OUTPUT_TOKENS))


def downgrade() -> None:
    op.execute('DELETE FROM "RoutePolicy" WHERE task = CAST(\'TRANSLATE\' AS "AiTask")')
    op.drop_column("UserPreference", "answerLanguage")
    op.drop_table("ClaimTranslation")


def _create_claim_translation() -> None:
    op.create_table(
        "ClaimTranslation",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("sourceSha256", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("ClaimTranslation_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ClaimTranslation_pkey")),
        sa.UniqueConstraint("claimId", "language", name=op.f("ClaimTranslation_claimId_language_key")),
    )
