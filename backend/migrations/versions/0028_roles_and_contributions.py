from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_roles_and_contributions"
down_revision: str | Sequence[str] | None = "0027_field_voices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ARTISAN = "ARTISAN"
DEMOTED_TO = "STUDENT"

ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("UserRole", ("ARTISAN",)),
    ("ConsentKind", ("ARTISAN_RECORDING", "GUARDIAN_CONSENT")),
    ("ClaimOrigin", ("ARTISAN",)),
    ("SourceOrigin", ("CONTRIBUTION",)),
    ("AiTask", ("INTERVIEW", "TESTIMONY")),
)

ENUM_COLUMNS: tuple[tuple[str, tuple[tuple[str, str, str | None], ...]], ...] = (
    (
        "UserRole",
        (
            ("User", "role", "STUDENT"),
            ("AccessRoster", "admitRole", None),
            ("Invite", "role", None),
            ("RoleRequest", "requestedRole", None),
            ("UsageEvent", "role", None),
            ("QuotaPolicy", "role", None),
        ),
    ),
    ("ConsentKind", (("ConsentRecord", "kind", None),)),
    ("ClaimOrigin", (("Claim", "origin", None),)),
    ("SourceOrigin", (("Source", "origin", "IMPORT"),)),
    ("AiTask", (("RoutePolicy", "task", None), ("UsageEvent", "task", None))),
)

ADD_UNCAPPED_ARTISAN = (
    "UPDATE \"AppSetting\" SET value = value || '{\"ARTISAN\": null}'::jsonb WHERE key = 'AI_ROLE_DAILY_USD' "
    "AND jsonb_typeof(value) = 'object' AND NOT (value ? 'ARTISAN')"
)

NEW_TABLES = (
    "StudentProfile",
    "ArtisanProfile",
    "ArtisanCraft",
    "ArtisanConversation",
    "ArtisanConversationAudio",
    "ArtisanContribution",
)

AGE_BANDS = ("UNDER_14", "14_17", "18_22", "23_PLUS")
GENDERS = ("WOMAN", "MAN", "ANOTHER", "UNSAID")
READING_STYLES = ("CHILD", "TEEN", "UNDERGRADUATE")
CREDIT_MODES = ("FULL_NAME", "FIRST_NAME", "CRAFT_AND_DISTRICT")
VOICE_PURPOSES = ("ASK", "ARTISAN")
VOICE_TRANSPORTS = ("AGENT", "RELAY")
CONTRIBUTION_STATUSES = ("PENDING", "APPROVED", "REJECTED", "WITHDRAWN")
ENGLISH_SOURCES = ("ORIGINAL", "MACHINE", "REVIEWED")
LOCATOR_PRECISIONS = ("WORD", "TURN")
EXTRACTION_STATUSES = ("PENDING", "RUNNING", "DONE", "NONE", "WAITING", "FAILED")
REJECT_REASONS = "'NOT_ABOUT_THE_CRAFT', 'MISHEARD', 'PERSONAL_DETAILS', 'ABOUT_OTHER_PEOPLE', 'DUPLICATE', 'UNCLEAR', 'OTHER'"
CONCEPT_TYPES = (
    "'ARTISAN_ACTION', 'PROCESS_STAGE', 'MATERIAL', 'TOOL', 'SENSORY_CUE', 'ARTISAN_DECISION', 'TRADITION', "
    "'HISTORICAL_CONTEXT', 'CHANGE', 'ENVIRONMENTAL_CONDITION', 'OUTCOME'"
)
DISCIPLINES = (
    "'OVERVIEW', 'PROCESS', 'CHEMISTRY', 'PHYSICS', 'MATERIALS', 'GEOGRAPHY', 'GEOLOGY', 'CLIMATE', 'ECOLOGY', "
    "'BOTANY', 'HISTORY', 'ECONOMICS', 'DESIGN', 'HEALTH'"
)

NOW = sa.text("now()")
NEW_ID = sa.text("gen_random_uuid()")
EMPTY_TEXTS = sa.text("ARRAY[]::text[]")
EMPTY = sa.text("'{}'")
STAMP = sa.DateTime(timezone=True)

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

ARTISAN_CLAIMS = "(SELECT id FROM \"Claim\" WHERE origin::text = 'ARTISAN')"
DELETE_TESTIMONY = (
    f'DELETE FROM "ReviewEvent" WHERE "claimId" IN {ARTISAN_CLAIMS}',
    f'DELETE FROM "ClaimSource" WHERE "claimId" IN {ARTISAN_CLAIMS}',
    "DELETE FROM \"Claim\" WHERE origin::text = 'ARTISAN'",
    "DELETE FROM \"Source\" WHERE origin::text = 'CONTRIBUTION'",
    'DELETE FROM "Concept" WHERE "originRef" = \'artisan-testimony\'',
    "UPDATE \"AppSetting\" SET value = value - 'ARTISAN' WHERE key = 'AI_ROLE_DAILY_USD'",
    "DELETE FROM \"ConsentRecord\" WHERE kind::text IN ('ARTISAN_RECORDING', 'GUARDIAN_CONSENT')",
)

VOCABULARY_CHECKS: tuple[tuple[str, str, Sequence[str] | str], ...] = (
    ("StudentProfile", "ageBand", AGE_BANDS),
    ("StudentProfile", "gender", GENDERS),
    ("ArtisanProfile", "creditMode", CREDIT_MODES),
    ("ArtisanConversation", "transport", VOICE_TRANSPORTS),
    ("ArtisanConversation", "extractionStatus", EXTRACTION_STATUSES),
    ("ArtisanContribution", "status", CONTRIBUTION_STATUSES),
    ("ArtisanContribution", "englishSource", ENGLISH_SOURCES),
    ("ArtisanContribution", "discipline", DISCIPLINES),
    ("ArtisanContribution", "conceptType", CONCEPT_TYPES),
    ("ArtisanContribution", "locatorPrecision", LOCATOR_PRECISIONS),
)
RULES: tuple[tuple[str, str, str], ...] = (
    ("ArtisanProfile", "creditName", '"creditMode" <> \'FULL_NAME\' OR "creditName" IS NOT NULL'),
    ("ArtisanProfile", "creditShortName", '"creditMode" <> \'FIRST_NAME\' OR "creditShortName" IS NOT NULL'),
    ("ArtisanCraft", "position", '"position" >= 1'),
    ("ArtisanContribution", "span", '"endMs" > "startMs"'),
    ("ArtisanContribution", "corroboratingClaimIds", 'cardinality("corroboratingClaimIds") <= 5'),
    (
        "ArtisanContribution",
        "approved",
        'status <> \'APPROVED\' OR ("claimId" IS NOT NULL AND "approvedAt" IS NOT NULL)',
    ),
    (
        "ArtisanContribution",
        "rejected",
        'status <> \'REJECTED\' OR ("rejectReason" IS NOT NULL AND "rejectedAt" IS NOT NULL)',
    ),
    ("ArtisanContribution", "withdrawn", "status <> 'WITHDRAWN' OR \"withdrawnAt\" IS NOT NULL"),
    (
        "ArtisanContribution",
        "textsCleared",
        "\"textsClearedAt\" IS NULL OR (status IN ('REJECTED', 'WITHDRAWN') "
        'AND quote IS NULL AND english IS NULL AND "claimText" IS NULL)',
    ),
)
FOREIGN_KEYS: tuple[tuple[str, str, str, str], ...] = (
    ("StudentProfile", "userId", "User.id", "CASCADE"),
    ("ArtisanProfile", "userId", "User.id", "CASCADE"),
    ("ArtisanProfile", "districtLgd", "AdminDistrict.lgd", "RESTRICT"),
    ("ArtisanCraft", "userId", "User.id", "CASCADE"),
    ("ArtisanCraft", "craftId", "Craft.id", "RESTRICT"),
    ("ArtisanConversation", "userId", "User.id", "CASCADE"),
    ("ArtisanConversation", "voiceSessionId", "VoiceSession.id", "SET NULL"),
    ("ArtisanConversation", "craftId", "Craft.id", "RESTRICT"),
    ("ArtisanConversation", "consentRecordId", "ConsentRecord.id", "SET NULL"),
    ("ArtisanConversation", "sourceId", "Source.id", "SET NULL"),
    ("ArtisanConversationAudio", "conversationId", "ArtisanConversation.id", "CASCADE"),
    ("ArtisanContribution", "conversationId", "ArtisanConversation.id", "RESTRICT"),
    ("ArtisanContribution", "userId", "User.id", "CASCADE"),
    ("ArtisanContribution", "craftId", "Craft.id", "RESTRICT"),
    ("ArtisanContribution", "claimId", "Claim.id", "SET NULL"),
    ("ArtisanContribution", "reviewedById", "User.id", "SET NULL"),
)
INDEXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ArtisanProfile", ("districtLgd",)),
    ("ArtisanCraft", ("craftId",)),
    ("ArtisanConversation", ("userId", "startedAt")),
    ("ArtisanConversation", ("craftId",)),
    ("ArtisanConversation", ("retentionUntil",)),
    ("ArtisanConversation", ("consentRecordId",)),
    ("ArtisanConversation", ("sourceId",)),
    ("ArtisanContribution", ("status", "createdAt")),
    ("ArtisanContribution", ("craftId", "status")),
    ("ArtisanContribution", ("userId", "createdAt")),
    ("ArtisanContribution", ("conversationId",)),
    ("ArtisanContribution", ("claimId",)),
    ("ArtisanContribution", ("reviewedById",)),
)


def _listed(values: Sequence[str]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _one_of(column: str, values: Sequence[str] | str) -> str:
    listed = values if isinstance(values, str) else _listed(values)
    return f'"{column}" IN ({listed})'


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for enum_name, values in ENUM_ADDITIONS:
            for value in values:
                op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")
    _add_columns()
    op.execute(ADD_UNCAPPED_ARTISAN)
    _create_profiles()
    _create_conversations()
    _create_conversation_audio()
    _create_contributions()
    _constrain()
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))


def downgrade() -> None:
    tasks = _listed(dict(ENUM_ADDITIONS)["AiTask"])
    op.execute(f'DELETE FROM "RoutePolicy" WHERE task::text IN ({tasks})')
    op.execute(f'DELETE FROM "UsageEvent" WHERE task::text IN ({tasks})')
    op.execute(sa.text('DELETE FROM "QuotaPolicy" WHERE role::text = :role').bindparams(role=ARTISAN))
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
    for statement in DELETE_TESTIMONY:
        op.execute(statement)
    op.drop_column("KnowledgePiece", "readingStyle")
    op.drop_column("VoiceSession", "purpose")
    op.drop_index(op.f("ConsentRecord_recordedById_idx"), table_name="ConsentRecord")
    op.drop_column("ConsentRecord", "recordedById")
    op.drop_column("ConsentRecord", "withdrawnAt")
    for enum_name, columns in ENUM_COLUMNS:
        _recreate_enum(enum_name, columns)


def _add_columns() -> None:
    op.add_column("ConsentRecord", sa.Column("recordedById", sa.UUID(), nullable=True))
    op.add_column("ConsentRecord", sa.Column("withdrawnAt", STAMP, nullable=True))
    recorder = op.f("ConsentRecord_recordedById_fkey")
    op.create_foreign_key(recorder, "ConsentRecord", "User", ["recordedById"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ConsentRecord_recordedById_idx"), "ConsentRecord", ["recordedById"])
    op.add_column(
        "VoiceSession", sa.Column("purpose", sa.String(length=16), server_default="ASK", nullable=False)
    )
    purpose_rule = _one_of("purpose", VOICE_PURPOSES)
    op.create_check_constraint(op.f("VoiceSession_purpose_check"), "VoiceSession", purpose_rule)
    op.add_column("KnowledgePiece", sa.Column("readingStyle", sa.String(length=16), nullable=True))
    style_rule = '"readingStyle" IS NULL OR ' + _one_of("readingStyle", READING_STYLES)
    op.create_check_constraint(op.f("KnowledgePiece_readingStyle_check"), "KnowledgePiece", style_rule)


def _recreate_enum(enum_name: str, columns: Sequence[tuple[str, str, str | None]]) -> None:
    query = sa.text(f'SELECT unnest(enum_range(NULL::"{enum_name}"))::text')
    added = dict(ENUM_ADDITIONS)[enum_name]
    before = [value for (value,) in op.get_bind().execute(query) if value not in added]
    op.execute(f'ALTER TYPE "{enum_name}" RENAME TO "{enum_name}_before_0028"')
    op.execute(f'CREATE TYPE "{enum_name}" AS ENUM ({_listed(before)})')
    for table, column, default in columns:
        if default is not None:
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" DROP DEFAULT')
        demoted = (
            f"CASE WHEN \"{column}\"::text = '{ARTISAN}' THEN '{DEMOTED_TO}' ELSE \"{column}\"::text END"
        )
        source = demoted if enum_name == "UserRole" else f'"{column}"::text'
        cast = f'({source})::"{enum_name}"'
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" TYPE "{enum_name}" USING {cast}')
        if default is not None:
            op.execute(f'ALTER TABLE "{table}" ALTER COLUMN "{column}" SET DEFAULT \'{default}\'')
    op.execute(f'DROP TYPE "{enum_name}_before_0028"')


def _constrain() -> None:
    for table, column, values in VOCABULARY_CHECKS:
        op.create_check_constraint(op.f(f"{table}_{column}_check"), table, _one_of(column, values))
    reason_rule = '"rejectReason" IS NULL OR ' + _one_of("rejectReason", REJECT_REASONS)
    op.create_check_constraint(
        op.f("ArtisanContribution_rejectReason_check"), "ArtisanContribution", reason_rule
    )
    for table, name, rule in RULES:
        op.create_check_constraint(op.f(f"{table}_{name}_check"), table, rule)
    for table, column, target, ondelete in FOREIGN_KEYS:
        referent, key = target.split(".")
        op.create_foreign_key(
            op.f(f"{table}_{column}_fkey"), table, referent, [column], [key], ondelete=ondelete
        )
    for table, columns in INDEXES:
        op.create_index(op.f(f"{table}_{'_'.join(columns)}_idx"), table, list(columns))
    op.create_index(
        "ArtisanConversation_extraction_unfinished_idx",
        "ArtisanConversation",
        ["extractionStatus"],
        postgresql_where=sa.text("\"extractionStatus\" NOT IN ('DONE', 'NONE')"),
    )


def _create_profiles() -> None:
    op.create_table(
        "StudentProfile",
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("ageBand", sa.String(length=16), nullable=False),
        sa.Column("gender", sa.String(length=16), nullable=False),
        sa.Column("completedAt", STAMP, nullable=False),
        sa.Column("createdAt", STAMP, server_default=NOW, nullable=False),
        sa.Column("updatedAt", STAMP, server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("userId", name=op.f("StudentProfile_pkey")),
    )
    op.create_table(
        "ArtisanProfile",
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("districtLgd", sa.Integer(), nullable=False),
        sa.Column("spokenLanguage", sa.String(length=16), nullable=False),
        sa.Column("creditMode", sa.String(length=24), nullable=False),
        sa.Column("creditName", sa.String(length=120), nullable=True),
        sa.Column("creditShortName", sa.String(length=60), nullable=True),
        sa.Column("adultConfirmedAt", STAMP, nullable=False),
        sa.Column("completedAt", STAMP, nullable=False),
        sa.Column("createdAt", STAMP, server_default=NOW, nullable=False),
        sa.Column("updatedAt", STAMP, server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("userId", name=op.f("ArtisanProfile_pkey")),
    )
    op.create_table(
        "ArtisanCraft",
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("userId", "craftId", name=op.f("ArtisanCraft_pkey")),
        sa.UniqueConstraint("userId", "position", name=op.f("ArtisanCraft_userId_position_key")),
    )


def _create_conversations() -> None:
    op.create_table(
        "ArtisanConversation",
        sa.Column("id", sa.UUID(), server_default=NEW_ID, nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("voiceSessionId", sa.UUID(), nullable=True),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("transport", sa.String(length=16), nullable=False),
        sa.Column("consentRecordId", sa.UUID(), nullable=True),
        sa.Column("consentVersion", sa.String(length=40), nullable=False),
        sa.Column("startedAt", STAMP, nullable=False),
        sa.Column("endedAt", STAMP, nullable=True),
        sa.Column("transcriptEnc", sa.Text(), nullable=True),
        sa.Column("topicsAsked", postgresql.ARRAY(sa.Text()), server_default=EMPTY_TEXTS, nullable=False),
        sa.Column("extractionStatus", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column("extractionAttempts", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("extractedAt", STAMP, nullable=True),
        sa.Column("sourceId", sa.UUID(), nullable=True),
        sa.Column("retentionUntil", STAMP, nullable=True),
        sa.Column("deletedAt", STAMP, nullable=True),
        sa.Column("createdAt", STAMP, server_default=NOW, nullable=False),
        sa.Column("updatedAt", STAMP, server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("ArtisanConversation_pkey")),
        sa.UniqueConstraint("voiceSessionId", name=op.f("ArtisanConversation_voiceSessionId_key")),
    )


def _create_conversation_audio() -> None:
    op.create_table(
        "ArtisanConversationAudio",
        sa.Column("id", sa.UUID(), server_default=NEW_ID, nullable=False),
        sa.Column("conversationId", sa.UUID(), nullable=False),
        sa.Column("turnId", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.SmallInteger(), nullable=False),
        sa.Column("objectKey", sa.Text(), nullable=False),
        sa.Column("mimeType", sa.String(length=80), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("durationMs", sa.Integer(), nullable=False),
        sa.Column("startMs", sa.Integer(), nullable=False),
        sa.Column("createdAt", STAMP, server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("ArtisanConversationAudio_pkey")),
        sa.UniqueConstraint("objectKey", name=op.f("ArtisanConversationAudio_objectKey_key")),
        sa.UniqueConstraint(
            "conversationId", "turnId", name=op.f("ArtisanConversationAudio_conversationId_turnId_key")
        ),
    )


def _create_contributions() -> None:
    op.create_table(
        "ArtisanContribution",
        sa.Column("id", sa.UUID(), server_default=NEW_ID, nullable=False),
        sa.Column("conversationId", sa.UUID(), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("turnId", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column("quote", sa.String(length=300), nullable=True),
        sa.Column("quoteLanguage", sa.String(length=16), nullable=False),
        sa.Column("english", sa.String(length=600), nullable=True),
        sa.Column("englishSource", sa.String(length=16), nullable=False),
        sa.Column("claimText", sa.String(length=300), nullable=True),
        sa.Column("discipline", sa.String(length=16), nullable=False),
        sa.Column("conceptType", sa.String(length=40), nullable=False),
        sa.Column("conceptName", sa.String(length=120), nullable=False),
        sa.Column("startMs", sa.Integer(), nullable=False),
        sa.Column("endMs", sa.Integer(), nullable=False),
        sa.Column("locatorPrecision", sa.String(length=8), nullable=False),
        sa.Column("screens", postgresql.ARRAY(sa.Text()), server_default=EMPTY, nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=True),
        sa.Column("corroboratingClaimIds", postgresql.ARRAY(sa.UUID()), server_default=EMPTY, nullable=False),
        sa.Column("reviewedById", sa.UUID(), nullable=True),
        sa.Column("reviewedAt", STAMP, nullable=True),
        sa.Column("approvedAt", STAMP, nullable=True),
        sa.Column("rejectedAt", STAMP, nullable=True),
        sa.Column("withdrawnAt", STAMP, nullable=True),
        sa.Column("rejectReason", sa.String(length=32), nullable=True),
        sa.Column("reviewNote", sa.String(length=500), nullable=True),
        sa.Column("textsClearedAt", STAMP, nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("createdAt", STAMP, server_default=NOW, nullable=False),
        sa.Column("updatedAt", STAMP, server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("ArtisanContribution_pkey")),
    )
