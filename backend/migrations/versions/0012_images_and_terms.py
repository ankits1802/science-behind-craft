from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_images_and_terms"
down_revision: str | Sequence[str] | None = "0011_first_password_proof"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = ("MediaRef", "MediaRefClaim", "Term", "TermCraft", "TermConcept", "TermSummary")
SUMMARISE_OUTPUT_TOKENS = 2048
SUMMARISE_ROUTES: list[dict] = [
    {"ordinal": 1, "provider": "GEMINI", "model": "gemini-3.5-flash-lite"},
    {"ordinal": 2, "provider": "ANTHROPIC", "model": "claude-haiku-5-5"},
    {"ordinal": 3, "provider": "OPENAI", "model": "gpt-6-luna"},
]

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

INSERT_ROUTE = (
    'INSERT INTO "RoutePolicy" (task, ordinal, "providerId", model, "maxOutputTokens") '
    'SELECT CAST(\'SUMMARISE\' AS "AiTask"), :ordinal, p.id, :model, :tokens FROM "Provider" p '
    'WHERE p.name = CAST(:provider AS "AiProvider") '
    "ON CONFLICT (task, ordinal) DO NOTHING"
)


def upgrade() -> None:
    _create_media_refs()
    _create_media_ref_claims()
    _create_terms()
    _create_term_crafts()
    _create_term_concepts()
    _create_term_summaries()
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))
    for route in SUMMARISE_ROUTES:
        op.execute(sa.text(INSERT_ROUTE).bindparams(**route, tokens=SUMMARISE_OUTPUT_TOKENS))


def downgrade() -> None:
    op.execute('DELETE FROM "RoutePolicy" WHERE task = CAST(\'SUMMARISE\' AS "AiTask")')
    for table in reversed(NEW_TABLES):
        op.drop_table(table)


def _create_media_refs() -> None:
    op.create_table(
        "MediaRef",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("urlKey", sa.String(length=64), nullable=False),
        sa.Column("display", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("pageUrl", sa.Text(), nullable=False),
        sa.Column("imageUrl", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("alt", sa.String(length=300), nullable=False),
        sa.Column("author", sa.String(length=300), nullable=True),
        sa.Column("site", sa.String(length=300), nullable=False),
        sa.Column("credit", sa.String(length=300), nullable=True),
        sa.Column("licence", sa.String(length=200), nullable=True),
        sa.Column("licenceUrl", sa.Text(), nullable=True),
        sa.Column("sourceId", sa.UUID(), nullable=True),
        sa.Column("retrievedAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("\"display\" IN ('INLINE', 'LINK_CARD')", name=op.f("MediaRef_display_check")),
        sa.CheckConstraint("num_nonnulls(width, height) <> 1", name=op.f("MediaRef_size_check")),
        sa.ForeignKeyConstraint(
            ["sourceId"], ["Source.id"], name=op.f("MediaRef_sourceId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("MediaRef_pkey")),
        sa.UniqueConstraint("urlKey", name=op.f("MediaRef_urlKey_key")),
    )
    op.create_index(op.f("MediaRef_sourceId_idx"), "MediaRef", ["sourceId"], unique=False)


def _create_media_ref_claims() -> None:
    op.create_table(
        "MediaRefClaim",
        sa.Column("mediaRefId", sa.UUID(), nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("relevance", sa.String(length=16), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("\"relevance\" IN ('TEXT', 'VISION')", name=op.f("MediaRefClaim_relevance_check")),
        sa.ForeignKeyConstraint(
            ["mediaRefId"], ["MediaRef.id"], name=op.f("MediaRefClaim_mediaRefId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("MediaRefClaim_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("mediaRefId", "claimId", name=op.f("MediaRefClaim_pkey")),
    )
    op.create_index(op.f("MediaRefClaim_claimId_idx"), "MediaRefClaim", ["claimId"], unique=False)


def _create_terms() -> None:
    op.create_table(
        "Term",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=True),
        sa.Column(
            "localNames",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("ARRAY[]::text[]"),
            nullable=False,
        ),
        sa.Column(
            "aliases", postgresql.ARRAY(sa.Text()), server_default=sa.text("ARRAY[]::text[]"), nullable=False
        ),
        sa.Column("wikidataId", sa.String(length=20), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("Term_pkey")),
        sa.UniqueConstraint("key", name=op.f("Term_key_key")),
    )


def _create_term_crafts() -> None:
    op.create_table(
        "TermCraft",
        sa.Column("termId", sa.UUID(), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["termId"], ["Term.id"], name=op.f("TermCraft_termId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("TermCraft_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("termId", "craftId", name=op.f("TermCraft_pkey")),
    )
    op.create_index(op.f("TermCraft_craftId_idx"), "TermCraft", ["craftId"], unique=False)


def _create_term_concepts() -> None:
    op.create_table(
        "TermConcept",
        sa.Column("termId", sa.UUID(), nullable=False),
        sa.Column("conceptId", sa.UUID(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["termId"], ["Term.id"], name=op.f("TermConcept_termId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["conceptId"], ["Concept.id"], name=op.f("TermConcept_conceptId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("termId", "conceptId", name=op.f("TermConcept_pkey")),
    )
    op.create_index(op.f("TermConcept_conceptId_idx"), "TermConcept", ["conceptId"], unique=False)


def _create_term_summaries() -> None:
    op.create_table(
        "TermSummary",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("termId", sa.UUID(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("basis", sa.String(length=16), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "claimIds", postgresql.ARRAY(sa.UUID()), server_default=sa.text("ARRAY[]::uuid[]"), nullable=False
        ),
        sa.Column("checkedAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "\"basis\" IN ('STORED', 'WIKIPEDIA', 'WEB_SEARCH')", name=op.f("TermSummary_basis_check")
        ),
        sa.ForeignKeyConstraint(
            ["termId"], ["Term.id"], name=op.f("TermSummary_termId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("TermSummary_pkey")),
        sa.UniqueConstraint("termId", "language", name=op.f("TermSummary_termId_language_key")),
    )
