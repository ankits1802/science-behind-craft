import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography, Geometry
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXTENSIONS = ("vector", "postgis", "pg_trgm", "unaccent", "citext")

APPEND_ONLY_TABLES = ("AuditLog", "ReviewEvent")

ENUMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("UserRole", ("MASTER_ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT")),
    ("AuthProvider", ("LOCAL", "GOOGLE")),
    ("AccessStatus", ("ACTIVE", "PENDING", "REJECTED", "SUSPENDED")),
    ("CredentialLinkPurpose", ("INVITE", "RESET")),
    ("RoleRequestStatus", ("PENDING", "APPROVED", "REJECTED")),
    ("ConsentKind", ("PRIVACY_NOTICE", "VOICE_NOTICE")),
    ("DataRequestKind", ("EXPORT", "DELETE")),
    ("DataRequestStatus", ("PENDING", "RUNNING", "COMPLETED", "FAILED")),
    ("ActorKind", ("USER", "SYSTEM")),
    ("AuthNoncePurpose", ("GOOGLE_SIGN_IN", "GOOGLE_LINK")),
    ("AiProvider", ("OPENAI", "GEMINI", "ANTHROPIC", "DEEPSEEK")),
    (
        "AiTask",
        (
            "PROOFREAD",
            "EXPAND",
            "SUMMARISE",
            "TRANSLATE",
            "TRANSCRIBE",
            "CAPTION",
            "PLAN",
            "COMPOSE",
            "WEB_READ",
            "EXTRACT",
            "EMBED",
            "IMAGE",
            "VIDEO",
            "VOICE_TURN",
            "EVAL_JUDGE",
        ),
    ),
    ("ProviderDataClass", ("PUBLIC_TEXT_ONLY", "ANY")),
    (
        "UsageOutcome",
        ("RESERVED", "OK", "ERROR", "REFUSED_CEILING", "REFUSED_QUOTA", "REFUSED_PROVIDER", "CANCELLED"),
    ),
    ("QuotaResource", ("TEXT_Q", "DEEP_Q", "VOICE_SECONDS", "IMAGE", "VIDEO", "ENRICHMENT_USD", "USD_DAY")),
    ("CraftStatus", ("ACTIVE", "LEGACY", "MERGED")),
    ("GiStatus", ("GI", "NON_GI")),
    (
        "AliasSource",
        (
            "MASTER",
            "CROSS_PORTAL_CODE",
            "CURATED",
            "IMMERSIVE",
            "CXA",
            "DR_SYNC",
            "PROPOSED",
            "WIKIDATA",
            "TRANSLITERATION",
        ),
    ),
    ("AliasStatus", ("PROPOSED", "ACTIVE", "REJECTED")),
    ("LocationPrecision", ("STATE", "DISTRICT", "POINT")),
    ("BoundarySource", ("SOI_1M", "KAGGLE_INDICATIVE")),
    ("EvidenceLevel", ("VERIFIED", "REVIEWED", "PROVISIONAL", "HYPOTHESIS")),
    (
        "EnvStat",
        (
            "DISTRICT_MEAN",
            "DISTRICT_P10",
            "DISTRICT_P90",
            "UNCERTAINTY_Q05_MEAN",
            "UNCERTAINTY_Q95_MEAN",
            "SHARE",
            "CLASS",
            "NORMAL",
            "DISTRICT_MIN",
            "DISTRICT_MAX",
            "TOTAL",
            "DENSITY",
            "DISTANCE",
            "COUNT",
        ),
    ),
    (
        "SourceKind",
        (
            "PAPER",
            "BOOK",
            "BOOK_CHAPTER",
            "WEB_PAGE",
            "ENCYCLOPEDIA",
            "DATASET",
            "GI_JOURNAL",
            "GOVERNMENT_REPORT",
            "COMPOUND_RECORD",
            "FIELD_TESTIMONY",
            "OTHER",
        ),
    ),
    ("Reliability", ("A", "B", "C", "D")),
    ("SourceStorage", ("FULL_TEXT", "EXCERPT", "LINK_ONLY")),
    ("SourceOrigin", ("IMPORT", "ENRICHMENT", "LIVE_RESEARCH")),
    ("Sensitivity", ("OPEN", "ATTRIBUTE_REQUIRED", "RESTRICTED")),
    ("ChunkAcl", ("PUBLIC", "RESEARCHER")),
    (
        "ConceptType",
        (
            "MATERIAL",
            "TOOL",
            "PROCESS_STAGE",
            "MECHANISM",
            "ENVIRONMENTAL_CONDITION",
            "ARTISAN_DECISION",
            "OUTCOME",
            "OPEN_QUESTION",
            "TRADITION",
            "DESIGN_PRINCIPLE",
            "HISTORICAL_CONTEXT",
            "COMPARISON",
            "EXPLANATION",
            "ARTISAN_ACTION",
            "SENSORY_CUE",
            "PROPERTY",
            "CHANGE",
            "CONCEPT",
        ),
    ),
    (
        "ConceptRelation",
        (
            "PRECEDES",
            "USES",
            "PRODUCES",
            "SCIENTIFICALLY_EXPLAINED_BY",
            "AFFECTED_BY",
            "PART_OF",
            "DEPENDS_ON",
            "CAUSES",
            "ENABLES",
            "EXPLAINS",
            "REQUIRES",
            "PRACTITIONER_EXPLAINS",
            "HAS_PROPERTY",
            "CONTRASTS_WITH",
            "ASSOCIATED_WITH",
            "SIMILAR_TO",
            "USED_FOR",
            "PREVENTS",
            "MODIFIES",
        ),
    ),
    (
        "StageType",
        (
            "PREP",
            "SCOUR",
            "MORDANT",
            "DYE",
            "RESIST",
            "PRINT",
            "WASH",
            "DRY",
            "SHAPE",
            "CARVE",
            "FIRE",
            "CAST",
            "FINISH",
            "OTHER",
        ),
    ),
    (
        "MaterialKind",
        ("FIBRE", "DYE", "MORDANT", "MINERAL", "CLAY", "METAL", "WOOD", "RESIN", "FUEL", "WATER", "OTHER"),
    ),
    (
        "MaterialRole",
        ("INPUT", "MORDANT", "DYE", "RESIST", "BINDER", "FLUX", "FUEL", "TOOL", "PRODUCT", "OTHER"),
    ),
    (
        "ReactionKind",
        (
            "REDOX",
            "ACID_BASE",
            "COMPLEXATION",
            "PRECIPITATION",
            "DEHYDRATION",
            "DEHYDROXYLATION",
            "PHASE_CHANGE",
            "POLYMERISATION",
            "HYDROLYSIS",
            "OTHER",
        ),
    ),
    ("ClaimOrigin", ("IMPORT", "RESEARCHER", "ENRICHMENT", "MODEL", "LIVE_RESEARCH")),
    ("ClaimStatus", ("DRAFT", "PROPOSED", "IN_REVIEW", "APPROVED", "REJECTED", "RETRACTED")),
    ("QuoteCheck", ("PASS", "FAIL", "NA")),
    ("SourceRelation", ("DIRECT", "CONTEXTUAL", "ANALOGOUS", "GENERAL_PRINCIPLE")),
    ("LiveTier", ("T3", "T4")),
    ("JobStatus", ("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "BLOCKED", "CANCELLED")),
    ("ObjectionKind", ("FACTUAL", "ATTRIBUTION", "SACRED_OR_RESTRICTED", "DEPICTION", "OTHER")),
    ("ObjectionStatus", ("OPEN", "ACKNOWLEDGED", "UPHELD", "DISMISSED")),
    ("AnswerMode", ("VERIFIED", "HYBRID", "DEEP")),
    ("Channel", ("TEXT", "VOICE")),
    ("MessageRole", ("USER", "ASSISTANT", "SYSTEM")),
    ("MediaKind", ("IMAGE", "VIDEO")),
    ("MediaVisibility", ("PRIVATE", "CRAFT_SHARED")),
    ("EvalRunStatus", ("QUEUED", "RUNNING", "SUCCEEDED", "FAILED")),
)

TABLES: tuple[str, ...] = (
    "AdminState",
    "CraftCategory",
    "CraftCode",
    "EnvDataset",
    "EvalRun",
    "Job",
    "PasswordResetRequest",
    "Provider",
    "QuotaPolicy",
    "SecretTestResult",
    "User",
    "WebFetch",
    "AccessRoster",
    "AdminDistrict",
    "AppSetting",
    "AuditLog",
    "AuthNonce",
    "Claim",
    "ConsentRecord",
    "CraftSpelling",
    "CraftSubCategory",
    "CxaCraftMap",
    "DataRequest",
    "EvalCase",
    "Invite",
    "ManagedSecret",
    "PasswordResetToken",
    "QuotaLedger",
    "RoleRequest",
    "RoutePolicy",
    "Source",
    "TwoFactorChallenge",
    "UsageEvent",
    "Chunk",
    "Compound",
    "Craft",
    "DistrictEnvValue",
    "DistrictGeology",
    "EvalResult",
    "ReviewEvent",
    "ClaimSource",
    "Concept",
    "Conversation",
    "CraftAlias",
    "CraftLocation",
    "EnrichmentJob",
    "GiRegistration",
    "Process",
    "Answer",
    "ConceptEdge",
    "EnrichmentProposal",
    "Material",
    "ProcessStage",
    "VoiceSession",
    "AnswerSentence",
    "AnswerTrace",
    "LiveCandidate",
    "MediaJob",
    "Message",
    "Reaction",
    "StageMaterial",
    "AnswerCitation",
    "MediaAsset",
    "Objection",
    "SavedItem",
    "UserPreference",
)

PROVIDERS: list[dict] = [
    {
        "name": "OPENAI",
        "preset": "openai",
        "kind": "openai",
        "baseUrl": "https://api.openai.com/v1",
        "apiKeySecretKey": "OPENAI_API_KEY",
        "dataClass": "ANY",
        "maxConcurrency": 6,
    },
    {
        "name": "GEMINI",
        "preset": "gemini",
        "kind": "gemini",
        "baseUrl": None,
        "apiKeySecretKey": "GEMINI_API_KEY",
        "dataClass": "ANY",
        "maxConcurrency": 8,
    },
    {
        "name": "ANTHROPIC",
        "preset": "anthropic",
        "kind": "anthropic",
        "baseUrl": None,
        "apiKeySecretKey": "ANTHROPIC_API_KEY",
        "dataClass": "ANY",
        "maxConcurrency": 6,
    },
    {
        "name": "DEEPSEEK",
        "preset": "deepseek",
        "kind": "openai_compatible",
        "baseUrl": "https://api.deepseek.com",
        "apiKeySecretKey": "DEEPSEEK_API_KEY",
        "dataClass": "PUBLIC_TEXT_ONLY",
        "maxConcurrency": 4,
    },
]

ROUTES: list[dict] = [
    {"task": "PLAN", "ordinal": 1, "provider": "GEMINI", "model": "gemini-3.5-flash-lite"},
    {"task": "PLAN", "ordinal": 2, "provider": "ANTHROPIC", "model": "claude-haiku-5-5"},
    {"task": "PLAN", "ordinal": 3, "provider": "OPENAI", "model": "gpt-6-luna"},
    {"task": "WEB_READ", "ordinal": 1, "provider": "GEMINI", "model": "gemini-3.5-flash-lite"},
    {"task": "WEB_READ", "ordinal": 2, "provider": "DEEPSEEK", "model": "deepseek-flash"},
    {"task": "WEB_READ", "ordinal": 3, "provider": "ANTHROPIC", "model": "claude-haiku-5-5"},
    {"task": "COMPOSE", "ordinal": 1, "provider": "ANTHROPIC", "model": "claude-sonnet-5-5"},
    {"task": "COMPOSE", "ordinal": 2, "provider": "GEMINI", "model": "gemini-3.8-flash"},
    {"task": "COMPOSE", "ordinal": 3, "provider": "OPENAI", "model": "gpt-6.1-terra"},
    {"task": "VOICE_TURN", "ordinal": 1, "provider": "GEMINI", "model": "gemini-3.8-flash"},
    {"task": "VOICE_TURN", "ordinal": 2, "provider": "ANTHROPIC", "model": "claude-haiku-5-5"},
    {"task": "VOICE_TURN", "ordinal": 3, "provider": "OPENAI", "model": "gpt-6-luna"},
    {"task": "EXTRACT", "ordinal": 1, "provider": "ANTHROPIC", "model": "claude-sonnet-5-5"},
    {"task": "EXTRACT", "ordinal": 2, "provider": "GEMINI", "model": "gemini-3.8-flash"},
    {"task": "EXTRACT", "ordinal": 3, "provider": "DEEPSEEK", "model": "deepseek-v4-pro"},
    {"task": "EMBED", "ordinal": 1, "provider": "GEMINI", "model": "gemini-embedding-2"},
    {"task": "EVAL_JUDGE", "ordinal": 1, "provider": "ANTHROPIC", "model": "claude-opus-5-5"},
    {"task": "EVAL_JUDGE", "ordinal": 2, "provider": "GEMINI", "model": "gemini-4-argon"},
    {"task": "IMAGE", "ordinal": 1, "provider": "GEMINI", "model": "gemini-3.1-flash-image"},
    {"task": "IMAGE", "ordinal": 2, "provider": "GEMINI", "model": "gemini-nano-banana-2.1"},
    {"task": "VIDEO", "ordinal": 1, "provider": "GEMINI", "model": "gemini-omni-1.2-flash"},
]

APP_SETTINGS: dict = {
    "AI_MONTHLY_CEILING_USD": 800.0,
    "AI_MEDIA_CAP_USD": 150.0,
    "AI_ROLE_DAILY_USD": {"STUDENT": 0.5, "RESEARCHER": 3.0, "PROFESSOR": 5.0, "MASTER_ADMIN": None},
    "AI_DEGRADE_AT_FRACTION": 0.8,
    "AI_MODEL_PRICES": {},
    "SIGN_UP_MODE": "ROSTER",
    "DOMAIN_ALLOWLIST": [],
}

QUOTAS: list[dict] = [
    {"role": "STUDENT", "resource": "VOICE_SECONDS", "perDay": 600},
    {"role": "STUDENT", "resource": "IMAGE", "perDay": 5},
    {"role": "STUDENT", "resource": "VIDEO", "perDay": 0},
    {"role": "RESEARCHER", "resource": "VOICE_SECONDS", "perDay": 1800},
    {"role": "RESEARCHER", "resource": "IMAGE", "perDay": 30},
    {"role": "RESEARCHER", "resource": "VIDEO", "perDay": 5},
    {"role": "PROFESSOR", "resource": "VOICE_SECONDS", "perDay": 1800},
    {"role": "PROFESSOR", "resource": "IMAGE", "perDay": 50},
    {"role": "PROFESSOR", "resource": "VIDEO", "perDay": 10},
    {"role": "MASTER_ADMIN", "resource": "VOICE_SECONDS", "perDay": None},
    {"role": "MASTER_ADMIN", "resource": "IMAGE", "perDay": None},
    {"role": "MASTER_ADMIN", "resource": "VIDEO", "perDay": None},
]


def _create_tables() -> None:
    op.create_table(
        "AdminState",
        sa.Column("lgd", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True
        ),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("lgd", name=op.f("AdminState_pkey")),
    )
    op.create_index("AdminState_geom_gist_idx", "AdminState", ["geom"], unique=False, postgresql_using="gist")
    op.create_table(
        "CraftCategory",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("sortOrder", sa.Integer(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("createdById", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("CraftCategory_pkey")),
        sa.UniqueConstraint("name", name=op.f("CraftCategory_name_key")),
        sa.UniqueConstraint("slug", name=op.f("CraftCategory_slug_key")),
    )
    op.create_table(
        "CraftCode",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("CraftCode_pkey")),
    )
    op.create_table(
        "EnvDataset",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("publisher", sa.String(length=300), nullable=True),
        sa.Column("edition", sa.String(length=120), nullable=True),
        sa.Column("period", sa.String(length=120), nullable=True),
        sa.Column("nativeResolution", sa.String(length=120), nullable=True),
        sa.Column("crs", sa.String(length=120), nullable=True),
        sa.Column("licence", sa.String(length=200), nullable=True),
        sa.Column("licenceUrl", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("redistributable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("retrievedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("citation", sa.Text(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("EnvDataset_pkey")),
        sa.UniqueConstraint("code", name=op.f("EnvDataset_code_key")),
    )
    op.create_table(
        "EvalRun",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("suite", sa.String(length=60), nullable=False),
        sa.Column("gitSha", sa.String(length=40), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "QUEUED", "RUNNING", "SUCCEEDED", "FAILED", name="EvalRunStatus", create_type=False
            ),
            server_default="QUEUED",
            nullable=False,
        ),
        sa.Column("budgetUsd", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("costUsd", sa.Numeric(precision=10, scale=6), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=True),
        sa.Column("reportKey", sa.Text(), nullable=True),
        sa.Column("startedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finishedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("EvalRun_pkey")),
    )
    op.create_table(
        "Job",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("queue", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "QUEUED",
                "RUNNING",
                "SUCCEEDED",
                "FAILED",
                "BLOCKED",
                "CANCELLED",
                name="JobStatus",
                create_type=False,
            ),
            server_default="QUEUED",
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("maxAttempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("runAfter", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("lockedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lockedBy", sa.String(length=120), nullable=True),
        sa.Column("lastError", sa.Text(), nullable=True),
        sa.Column("idempotencyKey", sa.String(length=160), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("Job_pkey")),
        sa.UniqueConstraint("idempotencyKey", name=op.f("Job_idempotencyKey_key")),
    )
    op.create_index(
        op.f("Job_queue_status_runAfter_idx"), "Job", ["queue", "status", "runAfter"], unique=False
    )
    op.create_table(
        "PasswordResetRequest",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("accountId", sa.UUID(), nullable=True),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("ipHash", sa.String(length=64), nullable=True),
        sa.Column("userAgent", sa.String(length=400), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("PasswordResetRequest_pkey")),
    )
    op.create_index(
        op.f("PasswordResetRequest_accountId_idx"), "PasswordResetRequest", ["accountId"], unique=False
    )
    op.create_index(
        op.f("PasswordResetRequest_createdAt_idx"), "PasswordResetRequest", ["createdAt"], unique=False
    )
    op.create_index(
        op.f("PasswordResetRequest_email_createdAt_idx"),
        "PasswordResetRequest",
        ["email", "createdAt"],
        unique=False,
    )
    op.create_table(
        "Provider",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "name",
            postgresql.ENUM(
                "OPENAI", "GEMINI", "ANTHROPIC", "DEEPSEEK", name="AiProvider", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("preset", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("baseUrl", sa.Text(), nullable=True),
        sa.Column("apiKeySecretKey", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("maxConcurrency", sa.Integer(), server_default=sa.text("4"), nullable=False),
        sa.Column(
            "dataClass",
            postgresql.ENUM("PUBLIC_TEXT_ONLY", "ANY", name="ProviderDataClass", create_type=False),
            server_default="ANY",
            nullable=False,
        ),
        sa.Column("learned", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("extra", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("Provider_pkey")),
        sa.UniqueConstraint("name", name=op.f("Provider_name_key")),
    )
    op.create_table(
        "QuotaPolicy",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "MASTER_ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT", name="UserRole", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "resource",
            postgresql.ENUM(
                "TEXT_Q",
                "DEEP_Q",
                "VOICE_SECONDS",
                "IMAGE",
                "VIDEO",
                "ENRICHMENT_USD",
                "USD_DAY",
                name="QuotaResource",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("perDay", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("perMonth", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("QuotaPolicy_pkey")),
        sa.UniqueConstraint("role", "resource", name=op.f("QuotaPolicy_role_resource_key")),
    )
    op.create_table(
        "SecretTestResult",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("checkedAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("SecretTestResult_pkey")),
        sa.UniqueConstraint("key", name=op.f("SecretTestResult_key_key")),
    )
    op.create_table(
        "User",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("passwordHash", sa.String(length=60), nullable=True),
        sa.Column("avatarUrl", sa.Text(), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM(
                "MASTER_ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT", name="UserRole", create_type=False
            ),
            server_default="STUDENT",
            nullable=False,
        ),
        sa.Column(
            "authProvider",
            postgresql.ENUM("LOCAL", "GOOGLE", name="AuthProvider", create_type=False),
            server_default="LOCAL",
            nullable=False,
        ),
        sa.Column("canManageQuestionnaire", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("canManageCrafts", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("canManageWorkshops", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("canReview", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("canViewProvenance", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("canDownloadDataset", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("passwordSetAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mustChangePassword", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("passwordIssuerKnown", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("firstLoginAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lastLoginAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sessionsValidFrom", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tokenVersion", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("twoFactorEnabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("twoFactorSecret", sa.Text(), nullable=True),
        sa.Column("twoFactorPendingSecret", sa.Text(), nullable=True),
        sa.Column("twoFactorPendingSince", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "twoFactorRecoveryCodes",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("ARRAY[]::text[]"),
            nullable=False,
        ),
        sa.Column("twoFactorLastStep", sa.Integer(), nullable=True),
        sa.Column("twoFactorEnabledAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("twoFactorFailedAttempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("twoFactorFailureWindowStartedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("twoFactorLockedUntil", sa.DateTime(timezone=True), nullable=True),
        sa.Column("twoFactorLockouts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "twoFactorRecoveryFailedAttempts", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("twoFactorRecoveryWindowStartedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("twoFactorRecoveryLockedUntil", sa.DateTime(timezone=True), nullable=True),
        sa.Column("twoFactorRecoveryLockouts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("emailVerifiedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("affiliation", sa.String(length=300), nullable=True),
        sa.Column("ageAttestedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("User_pkey")),
        sa.UniqueConstraint("email", name=op.f("User_email_key")),
    )
    op.create_index(op.f("User_createdAt_idx"), "User", ["createdAt"], unique=False)
    op.create_index(op.f("User_role_idx"), "User", ["role"], unique=False)
    op.create_table(
        "WebFetch",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("finalUrl", sa.Text(), nullable=True),
        sa.Column("status", sa.Integer(), nullable=True),
        sa.Column("contentType", sa.String(length=120), nullable=True),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("snapshotKey", sa.Text(), nullable=True),
        sa.Column("fetchedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blockedReason", sa.String(length=200), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("WebFetch_pkey")),
        sa.UniqueConstraint("sha256", name=op.f("WebFetch_sha256_key")),
    )
    op.create_index(op.f("WebFetch_url_idx"), "WebFetch", ["url"], unique=False)
    op.create_table(
        "AccessRoster",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE", "PENDING", "REJECTED", "SUSPENDED", name="AccessStatus", create_type=False
            ),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "admitRole",
            postgresql.ENUM(
                "MASTER_ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT", name="UserRole", create_type=False
            ),
            nullable=True,
        ),
        sa.Column("joinedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requestedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attemptCount", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lastAttemptAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decidedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decidedById", sa.UUID(), nullable=True),
        sa.Column("firstSeenAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fullName", sa.String(length=180), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("affiliation", sa.String(length=300), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("addedById", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["addedById"], ["User.id"], name=op.f("AccessRoster_addedById_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["decidedById"], ["User.id"], name=op.f("AccessRoster_decidedById_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("AccessRoster_pkey")),
        sa.UniqueConstraint("email", name=op.f("AccessRoster_email_key")),
    )
    op.create_index(op.f("AccessRoster_addedById_idx"), "AccessRoster", ["addedById"], unique=False)
    op.create_index(op.f("AccessRoster_createdAt_idx"), "AccessRoster", ["createdAt"], unique=False)
    op.create_index(op.f("AccessRoster_decidedById_idx"), "AccessRoster", ["decidedById"], unique=False)
    op.create_index(op.f("AccessRoster_status_idx"), "AccessRoster", ["status"], unique=False)
    op.create_index(
        op.f("AccessRoster_status_requestedAt_idx"), "AccessRoster", ["status", "requestedAt"], unique=False
    )
    op.create_table(
        "AdminDistrict",
        sa.Column("lgd", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("stateLgd", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False), nullable=True
        ),
        sa.Column("centroid", Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True),
        sa.Column(
            "boundarySource",
            postgresql.ENUM("SOI_1M", "KAGGLE_INDICATIVE", name="BoundarySource", create_type=False),
            server_default="KAGGLE_INDICATIVE",
            nullable=False,
        ),
        sa.Column("indicative", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["stateLgd"], ["AdminState.lgd"], name=op.f("AdminDistrict_stateLgd_fkey"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("lgd", name=op.f("AdminDistrict_pkey")),
    )
    op.create_index(
        "AdminDistrict_centroid_gist_idx",
        "AdminDistrict",
        ["centroid"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "AdminDistrict_geom_gist_idx", "AdminDistrict", ["geom"], unique=False, postgresql_using="gist"
    )
    op.create_index(op.f("AdminDistrict_stateLgd_idx"), "AdminDistrict", ["stateLgd"], unique=False)
    op.create_table(
        "AppSetting",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("updatedById", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["updatedById"], ["User.id"], name=op.f("AppSetting_updatedById_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("AppSetting_pkey")),
        sa.UniqueConstraint("key", name=op.f("AppSetting_key_key")),
    )
    op.create_table(
        "AuditLog",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actorId", sa.UUID(), nullable=True),
        sa.Column(
            "actorKind",
            postgresql.ENUM("USER", "SYSTEM", name="ActorKind", create_type=False),
            server_default="USER",
            nullable=False,
        ),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("targetType", sa.String(length=80), nullable=True),
        sa.Column("targetId", sa.String(length=120), nullable=True),
        sa.Column("detail", postgresql.JSONB(), nullable=True),
        sa.Column("ipHash", sa.String(length=64), nullable=True),
        sa.Column("requestId", sa.String(length=64), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["actorId"], ["User.id"], name=op.f("AuditLog_actorId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("AuditLog_pkey")),
    )
    op.create_index(op.f("AuditLog_action_createdAt_idx"), "AuditLog", ["action", "createdAt"], unique=False)
    op.create_index(op.f("AuditLog_actorId_idx"), "AuditLog", ["actorId"], unique=False)
    op.create_index(op.f("AuditLog_createdAt_idx"), "AuditLog", ["createdAt"], unique=False)
    op.create_index(
        op.f("AuditLog_targetType_targetId_idx"), "AuditLog", ["targetType", "targetId"], unique=False
    )
    op.create_table(
        "AuthNonce",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "purpose",
            postgresql.ENUM("GOOGLE_SIGN_IN", "GOOGLE_LINK", name="AuthNoncePurpose", create_type=False),
            nullable=False,
        ),
        sa.Column("nonceHash", sa.String(length=64), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=True),
        sa.Column("ipHash", sa.String(length=64), nullable=True),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("AuthNonce_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("AuthNonce_pkey")),
        sa.UniqueConstraint("nonceHash", name=op.f("AuthNonce_nonceHash_key")),
    )
    op.create_index(op.f("AuthNonce_expiresAt_idx"), "AuthNonce", ["expiresAt"], unique=False)
    op.create_table(
        "Claim",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("subjectType", sa.String(length=40), nullable=False),
        sa.Column("subjectId", sa.UUID(), nullable=False),
        sa.Column("predicate", sa.String(length=120), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("textLang", sa.String(length=16), server_default="en", nullable=False),
        sa.Column("valueNum", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("valueUnit", sa.String(length=40), nullable=True),
        sa.Column(
            "evidenceLevel",
            postgresql.ENUM(
                "VERIFIED", "REVIEWED", "PROVISIONAL", "HYPOTHESIS", name="EvidenceLevel", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("levelReason", sa.Text(), nullable=True),
        sa.Column(
            "origin",
            postgresql.ENUM(
                "IMPORT",
                "RESEARCHER",
                "ENRICHMENT",
                "MODEL",
                "LIVE_RESEARCH",
                name="ClaimOrigin",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "DRAFT",
                "PROPOSED",
                "IN_REVIEW",
                "APPROVED",
                "REJECTED",
                "RETRACTED",
                name="ClaimStatus",
                create_type=False,
            ),
            server_default="APPROVED",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("supersedesId", sa.UUID(), nullable=True),
        sa.Column("createdById", sa.UUID(), nullable=True),
        sa.Column(
            "createdByKind",
            postgresql.ENUM("USER", "SYSTEM", name="ActorKind", create_type=False),
            server_default="SYSTEM",
            nullable=False,
        ),
        sa.Column(
            "sensitivity",
            postgresql.ENUM(
                "OPEN", "ATTRIBUTE_REQUIRED", "RESTRICTED", name="Sensitivity", create_type=False
            ),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("sourcesDiffer", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english'::regconfig, coalesce(\"text\", ''))", persisted=True),
            nullable=False,
        ),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["createdById"], ["User.id"], name=op.f("Claim_createdById_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["supersedesId"], ["Claim.id"], name=op.f("Claim_supersedesId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Claim_pkey")),
    )
    op.create_index(
        "Claim_embedding_hnsw_idx",
        "Claim",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        op.f("Claim_subjectType_subjectId_evidenceLevel_status_idx"),
        "Claim",
        ["subjectType", "subjectId", "evidenceLevel", "status"],
        unique=False,
    )
    op.create_index(op.f("Claim_supersedesId_idx"), "Claim", ["supersedesId"], unique=False)
    op.create_index("Claim_tsv_gin_idx", "Claim", ["tsv"], unique=False, postgresql_using="gin")
    op.create_table(
        "ConsentRecord",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM("PRIVACY_NOTICE", "VOICE_NOTICE", name="ConsentKind", create_type=False),
            nullable=False,
        ),
        sa.Column("noticeVersion", sa.String(length=40), nullable=False),
        sa.Column("acceptedAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("ConsentRecord_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ConsentRecord_pkey")),
    )
    op.create_index(op.f("ConsentRecord_userId_kind_idx"), "ConsentRecord", ["userId", "kind"], unique=False)
    op.create_table(
        "CraftSpelling",
        sa.Column("spelling", sa.String(length=300), nullable=False),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column("craftCode", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=40), server_default="SHARED", nullable=False),
        sa.Column("createdById", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["craftCode"], ["CraftCode.code"], name=op.f("CraftSpelling_craftCode_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("spelling", name=op.f("CraftSpelling_pkey")),
    )
    op.create_index(op.f("CraftSpelling_craftCode_idx"), "CraftSpelling", ["craftCode"], unique=False)
    op.create_table(
        "CraftSubCategory",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("categoryId", sa.UUID(), nullable=False),
        sa.Column("sortOrder", sa.Integer(), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("createdById", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["categoryId"],
            ["CraftCategory.id"],
            name=op.f("CraftSubCategory_categoryId_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("CraftSubCategory_pkey")),
        sa.UniqueConstraint("categoryId", "name", name=op.f("CraftSubCategory_categoryId_name_key")),
        sa.UniqueConstraint("slug", name=op.f("CraftSubCategory_slug_key")),
    )
    op.create_index(op.f("CraftSubCategory_categoryId_idx"), "CraftSubCategory", ["categoryId"], unique=False)
    op.create_table(
        "CxaCraftMap",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("cxaSlug", sa.String(length=200), nullable=False),
        sa.Column("craftSlug", sa.String(length=200), nullable=False),
        sa.Column("acceptedById", sa.UUID(), nullable=True),
        sa.Column("acceptedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["acceptedById"], ["User.id"], name=op.f("CxaCraftMap_acceptedById_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("CxaCraftMap_pkey")),
        sa.UniqueConstraint("cxaSlug", name=op.f("CxaCraftMap_cxaSlug_key")),
    )
    op.create_index(op.f("CxaCraftMap_craftSlug_idx"), "CxaCraftMap", ["craftSlug"], unique=False)
    op.create_table(
        "DataRequest",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=True),
        sa.Column(
            "kind",
            postgresql.ENUM("EXPORT", "DELETE", name="DataRequestKind", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING", "RUNNING", "COMPLETED", "FAILED", name="DataRequestStatus", create_type=False
            ),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("exportKey", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("completedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("DataRequest_userId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("DataRequest_pkey")),
    )
    op.create_index(op.f("DataRequest_status_idx"), "DataRequest", ["status"], unique=False)
    op.create_index(op.f("DataRequest_userId_idx"), "DataRequest", ["userId"], unique=False)
    op.create_table(
        "EvalCase",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("suite", sa.String(length=60), nullable=False),
        sa.Column("externalId", sa.String(length=120), nullable=False),
        sa.Column("craftSlug", sa.String(length=200), nullable=True),
        sa.Column("input", postgresql.JSONB(), nullable=False),
        sa.Column("expected", postgresql.JSONB(), nullable=False),
        sa.Column("authorId", sa.UUID(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["authorId"], ["User.id"], name=op.f("EvalCase_authorId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("EvalCase_pkey")),
        sa.UniqueConstraint("suite", "externalId", name=op.f("EvalCase_suite_externalId_key")),
    )
    op.create_table(
        "Invite",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "MASTER_ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT", name="UserRole", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("invitedById", sa.UUID(), nullable=True),
        sa.Column("tokenHash", sa.String(length=128), nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acceptedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revokedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["invitedById"], ["User.id"], name=op.f("Invite_invitedById_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Invite_pkey")),
        sa.UniqueConstraint("tokenHash", name=op.f("Invite_tokenHash_key")),
    )
    op.create_index(op.f("Invite_email_idx"), "Invite", ["email"], unique=False)
    op.create_index(op.f("Invite_invitedById_idx"), "Invite", ["invitedById"], unique=False)
    op.create_table(
        "ManagedSecret",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("valueEnc", sa.Text(), nullable=False),
        sa.Column("hint", sa.String(length=16), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lastStatus", sa.String(length=16), server_default="UNKNOWN", nullable=False),
        sa.Column("lastCheckedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lastError", sa.Text(), nullable=True),
        sa.Column("updatedById", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["updatedById"], ["User.id"], name=op.f("ManagedSecret_updatedById_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ManagedSecret_pkey")),
        sa.UniqueConstraint("key", name=op.f("ManagedSecret_key_key")),
    )
    op.create_index(op.f("ManagedSecret_updatedById_idx"), "ManagedSecret", ["updatedById"], unique=False)
    op.create_table(
        "PasswordResetToken",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("tokenHash", sa.String(length=128), nullable=False),
        sa.Column(
            "purpose",
            postgresql.ENUM("INVITE", "RESET", name="CredentialLinkPurpose", create_type=False),
            server_default="RESET",
            nullable=False,
        ),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revokedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("issuedById", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["issuedById"], ["User.id"], name=op.f("PasswordResetToken_issuedById_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("PasswordResetToken_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("PasswordResetToken_pkey")),
        sa.UniqueConstraint("tokenHash", name=op.f("PasswordResetToken_tokenHash_key")),
    )
    op.create_index(
        op.f("PasswordResetToken_issuedById_idx"), "PasswordResetToken", ["issuedById"], unique=False
    )
    op.create_index(
        op.f("PasswordResetToken_userId_createdAt_idx"),
        "PasswordResetToken",
        ["userId", "createdAt"],
        unique=False,
    )
    op.create_table(
        "QuotaLedger",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=True),
        sa.Column(
            "resource",
            postgresql.ENUM(
                "TEXT_Q",
                "DEEP_Q",
                "VOICE_SECONDS",
                "IMAGE",
                "VIDEO",
                "ENRICHMENT_USD",
                "USD_DAY",
                name="QuotaResource",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("units", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("refType", sa.String(length=60), nullable=True),
        sa.Column("refId", sa.String(length=120), nullable=True),
        sa.Column("idempotencyKey", sa.String(length=160), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("QuotaLedger_userId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("QuotaLedger_pkey")),
        sa.UniqueConstraint("idempotencyKey", name=op.f("QuotaLedger_idempotencyKey_key")),
    )
    op.create_index(
        op.f("QuotaLedger_userId_resource_createdAt_idx"),
        "QuotaLedger",
        ["userId", "resource", "createdAt"],
        unique=False,
    )
    op.create_table(
        "RoleRequest",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column(
            "requestedRole",
            postgresql.ENUM(
                "MASTER_ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT", name="UserRole", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("affiliation", sa.String(length=300), nullable=True),
        sa.Column("profileUrl", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("PENDING", "APPROVED", "REJECTED", name="RoleRequestStatus", create_type=False),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("decidedById", sa.UUID(), nullable=True),
        sa.Column("decidedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["decidedById"], ["User.id"], name=op.f("RoleRequest_decidedById_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("RoleRequest_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("RoleRequest_pkey")),
    )
    op.create_index(op.f("RoleRequest_status_idx"), "RoleRequest", ["status"], unique=False)
    op.create_index(op.f("RoleRequest_userId_idx"), "RoleRequest", ["userId"], unique=False)
    op.create_table(
        "RoutePolicy",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "task",
            postgresql.ENUM(
                "PROOFREAD",
                "EXPAND",
                "SUMMARISE",
                "TRANSLATE",
                "TRANSCRIBE",
                "CAPTION",
                "PLAN",
                "COMPOSE",
                "WEB_READ",
                "EXTRACT",
                "EMBED",
                "IMAGE",
                "VIDEO",
                "VOICE_TURN",
                "EVAL_JUDGE",
                name="AiTask",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("providerId", sa.UUID(), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("maxOutputTokens", sa.Integer(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("params", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("updatedById", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["providerId"], ["Provider.id"], name=op.f("RoutePolicy_providerId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["updatedById"], ["User.id"], name=op.f("RoutePolicy_updatedById_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("RoutePolicy_pkey")),
        sa.UniqueConstraint("task", "ordinal", name=op.f("RoutePolicy_task_ordinal_key")),
    )
    op.create_index(op.f("RoutePolicy_providerId_idx"), "RoutePolicy", ["providerId"], unique=False)
    op.create_table(
        "Source",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "PAPER",
                "BOOK",
                "BOOK_CHAPTER",
                "WEB_PAGE",
                "ENCYCLOPEDIA",
                "DATASET",
                "GI_JOURNAL",
                "GOVERNMENT_REPORT",
                "COMPOUND_RECORD",
                "FIELD_TESTIMONY",
                "OTHER",
                name="SourceKind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("publisher", sa.String(length=300), nullable=True),
        sa.Column("licence", sa.String(length=200), nullable=True),
        sa.Column(
            "reliability",
            postgresql.ENUM("A", "B", "C", "D", name="Reliability", create_type=False),
            server_default="C",
            nullable=False,
        ),
        sa.Column(
            "storage",
            postgresql.ENUM("FULL_TEXT", "EXCERPT", "LINK_ONLY", name="SourceStorage", create_type=False),
            server_default="LINK_ONLY",
            nullable=False,
        ),
        sa.Column("snapshotKey", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("retrievedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("addedById", sa.UUID(), nullable=True),
        sa.Column(
            "origin",
            postgresql.ENUM("IMPORT", "ENRICHMENT", "LIVE_RESEARCH", name="SourceOrigin", create_type=False),
            server_default="IMPORT",
            nullable=False,
        ),
        sa.Column(
            "sensitivity",
            postgresql.ENUM(
                "OPEN", "ATTRIBUTE_REQUIRED", "RESTRICTED", name="Sensitivity", create_type=False
            ),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("evidenceKind", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("externalIds", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["addedById"], ["User.id"], name=op.f("Source_addedById_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Source_pkey")),
    )
    op.create_index(
        "Source_doi_key", "Source", ["doi"], unique=True, postgresql_where=sa.text("doi IS NOT NULL")
    )
    op.create_index(op.f("Source_origin_idx"), "Source", ["origin"], unique=False)
    op.create_index(op.f("Source_url_idx"), "Source", ["url"], unique=False)
    op.create_table(
        "TwoFactorChallenge",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("usedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("TwoFactorChallenge_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("TwoFactorChallenge_pkey")),
    )
    op.create_index(
        op.f("TwoFactorChallenge_expiresAt_idx"), "TwoFactorChallenge", ["expiresAt"], unique=False
    )
    op.create_index(op.f("TwoFactorChallenge_userId_idx"), "TwoFactorChallenge", ["userId"], unique=False)
    op.create_table(
        "UsageEvent",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM(
                "MASTER_ADMIN", "PROFESSOR", "RESEARCHER", "STUDENT", name="UserRole", create_type=False
            ),
            nullable=True,
        ),
        sa.Column(
            "task",
            postgresql.ENUM(
                "PROOFREAD",
                "EXPAND",
                "SUMMARISE",
                "TRANSLATE",
                "TRANSCRIBE",
                "CAPTION",
                "PLAN",
                "COMPOSE",
                "WEB_READ",
                "EXTRACT",
                "EMBED",
                "IMAGE",
                "VIDEO",
                "VOICE_TURN",
                "EVAL_JUDGE",
                name="AiTask",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "provider",
            postgresql.ENUM(
                "OPENAI", "GEMINI", "ANTHROPIC", "DEEPSEEK", name="AiProvider", create_type=False
            ),
            nullable=True,
        ),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("routeOrdinal", sa.Integer(), nullable=True),
        sa.Column("inputTokens", sa.Integer(), nullable=True),
        sa.Column("outputTokens", sa.Integer(), nullable=True),
        sa.Column("cachedTokens", sa.Integer(), nullable=True),
        sa.Column("units", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=16), nullable=True),
        sa.Column(
            "estimatedCostUsd", sa.Numeric(precision=10, scale=6), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("costUsd", sa.Numeric(precision=10, scale=6), server_default=sa.text("0"), nullable=False),
        sa.Column("isMedia", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("latencyMs", sa.Integer(), nullable=True),
        sa.Column("requestId", sa.String(length=64), nullable=True),
        sa.Column(
            "outcome",
            postgresql.ENUM(
                "RESERVED",
                "OK",
                "ERROR",
                "REFUSED_CEILING",
                "REFUSED_QUOTA",
                "REFUSED_PROVIDER",
                "CANCELLED",
                name="UsageOutcome",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("errorKind", sa.String(length=40), nullable=True),
        sa.Column("detail", postgresql.JSONB(), nullable=True),
        sa.Column("settledAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("UsageEvent_userId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("UsageEvent_pkey")),
    )
    op.create_index(op.f("UsageEvent_createdAt_idx"), "UsageEvent", ["createdAt"], unique=False)
    op.create_index(
        op.f("UsageEvent_outcome_createdAt_idx"), "UsageEvent", ["outcome", "createdAt"], unique=False
    )
    op.create_index(op.f("UsageEvent_requestId_idx"), "UsageEvent", ["requestId"], unique=False)
    op.create_index(op.f("UsageEvent_task_createdAt_idx"), "UsageEvent", ["task", "createdAt"], unique=False)
    op.create_index(
        op.f("UsageEvent_userId_createdAt_idx"), "UsageEvent", ["userId", "createdAt"], unique=False
    )
    op.create_table(
        "Chunk",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sourceId", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("locator", sa.String(length=300), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english'::regconfig, coalesce(\"text\", ''))", persisted=True),
            nullable=False,
        ),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("lang", sa.String(length=16), server_default="en", nullable=False),
        sa.Column(
            "acl",
            postgresql.ENUM("PUBLIC", "RESEARCHER", name="ChunkAcl", create_type=False),
            server_default="PUBLIC",
            nullable=False,
        ),
        sa.Column(
            "sensitivity",
            postgresql.ENUM(
                "OPEN", "ATTRIBUTE_REQUIRED", "RESTRICTED", name="Sensitivity", create_type=False
            ),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["sourceId"], ["Source.id"], name=op.f("Chunk_sourceId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Chunk_pkey")),
        sa.UniqueConstraint("sourceId", "ordinal", name=op.f("Chunk_sourceId_ordinal_key")),
    )
    op.create_index(op.f("Chunk_acl_sensitivity_idx"), "Chunk", ["acl", "sensitivity"], unique=False)
    op.create_index(
        "Chunk_embedding_hnsw_idx",
        "Chunk",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("Chunk_tsv_gin_idx", "Chunk", ["tsv"], unique=False, postgresql_using="gin")
    op.create_table(
        "Compound",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pubchemCid", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("formula", sa.String(length=200), nullable=True),
        sa.Column("iupacName", sa.Text(), nullable=True),
        sa.Column("smiles", sa.Text(), nullable=True),
        sa.Column("inchiKey", sa.String(length=27), nullable=True),
        sa.Column("molecularWeight", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column(
            "synonyms", postgresql.ARRAY(sa.Text()), server_default=sa.text("ARRAY[]::text[]"), nullable=False
        ),
        sa.Column("hazards", postgresql.JSONB(), nullable=True),
        sa.Column("sourceId", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["sourceId"], ["Source.id"], name=op.f("Compound_sourceId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Compound_pkey")),
        sa.UniqueConstraint("inchiKey", name=op.f("Compound_inchiKey_key")),
        sa.UniqueConstraint("pubchemCid", name=op.f("Compound_pubchemCid_key")),
    )
    op.create_index(op.f("Compound_formula_idx"), "Compound", ["formula"], unique=False)
    op.create_table(
        "Craft",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("localName", sa.String(length=300), nullable=True),
        sa.Column("category", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("place", sa.Text(), nullable=True),
        sa.Column("extraMetadata", postgresql.JSONB(), nullable=True),
        sa.Column("recordedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("recordedTimezone", sa.String(length=64), server_default="Asia/Kolkata", nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("createdById", sa.UUID(), nullable=True),
        sa.Column("craftCode", sa.String(length=40), nullable=True),
        sa.Column(
            "slug",
            sa.String(length=200),
            server_default=sa.text("('craft-'::text || md5((random())::text || (clock_timestamp())::text))"),
            nullable=False,
        ),
        sa.Column("subCategoryId", sa.UUID(), nullable=True),
        sa.Column("sourceSerial", sa.Integer(), nullable=True),
        sa.Column(
            "stateOfOrigin",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("ARRAY[]::text[]"),
            nullable=False,
        ),
        sa.Column(
            "stateOfPractice",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("ARRAY[]::text[]"),
            nullable=False,
        ),
        sa.Column(
            "giStatus", postgresql.ENUM("GI", "NON_GI", name="GiStatus", create_type=False), nullable=True
        ),
        sa.Column("isCatchAll", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "sourceNotes",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("ARRAY[]::text[]"),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("ACTIVE", "LEGACY", "MERGED", name="CraftStatus", create_type=False),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("mergedIntoId", sa.UUID(), nullable=True),
        sa.Column("descriptorEmbedding", Vector(1536), nullable=True),
        sa.ForeignKeyConstraint(
            ["craftCode"], ["CraftCode.code"], name=op.f("Craft_craftCode_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["createdById"], ["User.id"], name=op.f("Craft_createdById_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["mergedIntoId"], ["Craft.id"], name=op.f("Craft_mergedIntoId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["subCategoryId"],
            ["CraftSubCategory.id"],
            name=op.f("Craft_subCategoryId_fkey"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Craft_pkey")),
        sa.UniqueConstraint("slug", name=op.f("Craft_slug_key")),
        sa.UniqueConstraint("sourceSerial", name=op.f("Craft_sourceSerial_key")),
        sa.UniqueConstraint("subCategoryId", "name", name=op.f("Craft_subCategoryId_name_key")),
    )
    op.create_index(op.f("Craft_craftCode_idx"), "Craft", ["craftCode"], unique=False)
    op.create_index(op.f("Craft_createdById_idx"), "Craft", ["createdById"], unique=False)
    op.create_index(
        "Craft_descriptorEmbedding_hnsw_idx",
        "Craft",
        ["descriptorEmbedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"descriptorEmbedding": "vector_cosine_ops"},
    )
    op.create_index(op.f("Craft_status_idx"), "Craft", ["status"], unique=False)
    op.create_index(op.f("Craft_subCategoryId_idx"), "Craft", ["subCategoryId"], unique=False)
    op.create_table(
        "DistrictEnvValue",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("districtLgd", sa.Integer(), nullable=False),
        sa.Column("datasetId", sa.UUID(), nullable=False),
        sa.Column("variable", sa.String(length=120), nullable=False),
        sa.Column("depthOrPeriod", sa.String(length=80), server_default="", nullable=False),
        sa.Column(
            "stat",
            postgresql.ENUM(
                "DISTRICT_MEAN",
                "DISTRICT_P10",
                "DISTRICT_P90",
                "UNCERTAINTY_Q05_MEAN",
                "UNCERTAINTY_Q95_MEAN",
                "SHARE",
                "CLASS",
                "NORMAL",
                "DISTRICT_MIN",
                "DISTRICT_MAX",
                "TOTAL",
                "DENSITY",
                "DISTANCE",
                "COUNT",
                name="EnvStat",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("valueText", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("pixelCount", sa.Integer(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["datasetId"], ["EnvDataset.id"], name=op.f("DistrictEnvValue_datasetId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["districtLgd"],
            ["AdminDistrict.lgd"],
            name=op.f("DistrictEnvValue_districtLgd_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("DistrictEnvValue_pkey")),
        sa.UniqueConstraint(
            "districtLgd",
            "datasetId",
            "variable",
            "depthOrPeriod",
            "stat",
            name=op.f("DistrictEnvValue_districtLgd_datasetId_variable_depthOrPeriod_stat_key"),
        ),
    )
    op.create_index(op.f("DistrictEnvValue_datasetId_idx"), "DistrictEnvValue", ["datasetId"], unique=False)
    op.create_table(
        "DistrictGeology",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("districtLgd", sa.Integer(), nullable=False),
        sa.Column("datasetId", sa.UUID(), nullable=False),
        sa.Column("lithology", sa.String(length=200), nullable=False),
        sa.Column("areaShare", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column("mineralOccurrences", postgresql.JSONB(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["datasetId"], ["EnvDataset.id"], name=op.f("DistrictGeology_datasetId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["districtLgd"],
            ["AdminDistrict.lgd"],
            name=op.f("DistrictGeology_districtLgd_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("DistrictGeology_pkey")),
        sa.UniqueConstraint(
            "districtLgd",
            "datasetId",
            "lithology",
            name=op.f("DistrictGeology_districtLgd_datasetId_lithology_key"),
        ),
    )
    op.create_index(op.f("DistrictGeology_datasetId_idx"), "DistrictGeology", ["datasetId"], unique=False)
    op.create_index(op.f("DistrictGeology_districtLgd_idx"), "DistrictGeology", ["districtLgd"], unique=False)
    op.create_table(
        "EvalResult",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("runId", sa.UUID(), nullable=False),
        sa.Column("caseId", sa.UUID(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("output", postgresql.JSONB(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["caseId"], ["EvalCase.id"], name=op.f("EvalResult_caseId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["runId"], ["EvalRun.id"], name=op.f("EvalResult_runId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("EvalResult_pkey")),
        sa.UniqueConstraint("runId", "caseId", name=op.f("EvalResult_runId_caseId_key")),
    )
    op.create_table(
        "ReviewEvent",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("actorId", sa.UUID(), nullable=True),
        sa.Column(
            "actorKind",
            postgresql.ENUM("USER", "SYSTEM", name="ActorKind", create_type=False),
            nullable=False,
        ),
        sa.Column("systemActor", sa.String(length=40), nullable=True),
        sa.Column(
            "fromStatus",
            postgresql.ENUM(
                "DRAFT",
                "PROPOSED",
                "IN_REVIEW",
                "APPROVED",
                "REJECTED",
                "RETRACTED",
                name="ClaimStatus",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "toStatus",
            postgresql.ENUM(
                "DRAFT",
                "PROPOSED",
                "IN_REVIEW",
                "APPROVED",
                "REJECTED",
                "RETRACTED",
                name="ClaimStatus",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "fromLevel",
            postgresql.ENUM(
                "VERIFIED", "REVIEWED", "PROVISIONAL", "HYPOTHESIS", name="EvidenceLevel", create_type=False
            ),
            nullable=True,
        ),
        sa.Column(
            "toLevel",
            postgresql.ENUM(
                "VERIFIED", "REVIEWED", "PROVISIONAL", "HYPOTHESIS", name="EvidenceLevel", create_type=False
            ),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["actorId"], ["User.id"], name=op.f("ReviewEvent_actorId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("ReviewEvent_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ReviewEvent_pkey")),
    )
    op.create_index(op.f("ReviewEvent_actorId_idx"), "ReviewEvent", ["actorId"], unique=False)
    op.create_index(
        op.f("ReviewEvent_claimId_createdAt_idx"), "ReviewEvent", ["claimId", "createdAt"], unique=False
    )
    op.create_table(
        "ClaimSource",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("sourceId", sa.UUID(), nullable=False),
        sa.Column("chunkId", sa.UUID(), nullable=True),
        sa.Column("locator", sa.String(length=300), nullable=True),
        sa.Column("quote", sa.String(length=300), nullable=True),
        sa.Column(
            "quoteCheck",
            postgresql.ENUM("PASS", "FAIL", "NA", name="QuoteCheck", create_type=False),
            server_default="NA",
            nullable=False,
        ),
        sa.Column("checkedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "relation",
            postgresql.ENUM(
                "DIRECT",
                "CONTEXTUAL",
                "ANALOGOUS",
                "GENERAL_PRINCIPLE",
                name="SourceRelation",
                create_type=False,
            ),
            server_default="DIRECT",
            nullable=False,
        ),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunkId"], ["Chunk.id"], name=op.f("ClaimSource_chunkId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("ClaimSource_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sourceId"], ["Source.id"], name=op.f("ClaimSource_sourceId_fkey"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ClaimSource_pkey")),
    )
    op.create_index(op.f("ClaimSource_claimId_idx"), "ClaimSource", ["claimId"], unique=False)
    op.create_index(op.f("ClaimSource_sourceId_idx"), "ClaimSource", ["sourceId"], unique=False)
    op.create_table(
        "Concept",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("subCategoryId", sa.UUID(), nullable=True),
        sa.Column(
            "type",
            postgresql.ENUM(
                "MATERIAL",
                "TOOL",
                "PROCESS_STAGE",
                "MECHANISM",
                "ENVIRONMENTAL_CONDITION",
                "ARTISAN_DECISION",
                "OUTCOME",
                "OPEN_QUESTION",
                "TRADITION",
                "DESIGN_PRINCIPLE",
                "HISTORICAL_CONTEXT",
                "COMPARISON",
                "EXPLANATION",
                "ARTISAN_ACTION",
                "SENSORY_CUE",
                "PROPERTY",
                "CHANGE",
                "CONCEPT",
                name="ConceptType",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("originRef", sa.Text(), nullable=True),
        sa.Column(
            "sensitivity",
            postgresql.ENUM(
                "OPEN", "ATTRIBUTE_REQUIRED", "RESTRICTED", name="Sensitivity", create_type=False
            ),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("Concept_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["subCategoryId"],
            ["CraftSubCategory.id"],
            name=op.f("Concept_subCategoryId_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Concept_pkey")),
    )
    op.create_index(op.f("Concept_craftId_type_idx"), "Concept", ["craftId", "type"], unique=False)
    op.create_index(op.f("Concept_subCategoryId_idx"), "Concept", ["subCategoryId"], unique=False)
    op.create_table(
        "Conversation",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column(
            "mode",
            postgresql.ENUM("VERIFIED", "HYBRID", "DEEP", name="AnswerMode", create_type=False),
            server_default="HYBRID",
            nullable=False,
        ),
        sa.Column(
            "channel",
            postgresql.ENUM("TEXT", "VOICE", name="Channel", create_type=False),
            server_default="TEXT",
            nullable=False,
        ),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("language", sa.String(length=16), server_default="en", nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("Conversation_craftId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("Conversation_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Conversation_pkey")),
    )
    op.create_index(
        op.f("Conversation_userId_updatedAt_idx"), "Conversation", ["userId", "updatedAt"], unique=False
    )
    op.create_table(
        "CraftAlias",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("alias", sa.String(length=300), nullable=False),
        sa.Column("aliasNorm", sa.String(length=300), nullable=False),
        sa.Column("script", sa.String(length=40), nullable=True),
        sa.Column("lang", sa.String(length=16), nullable=True),
        sa.Column(
            "source",
            postgresql.ENUM(
                "MASTER",
                "CROSS_PORTAL_CODE",
                "CURATED",
                "IMMERSIVE",
                "CXA",
                "DR_SYNC",
                "PROPOSED",
                "WIKIDATA",
                "TRANSLITERATION",
                name="AliasSource",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM("PROPOSED", "ACTIVE", "REJECTED", name="AliasStatus", create_type=False),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("addedById", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["addedById"], ["User.id"], name=op.f("CraftAlias_addedById_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("CraftAlias_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("CraftAlias_pkey")),
        sa.UniqueConstraint("craftId", "aliasNorm", name=op.f("CraftAlias_craftId_aliasNorm_key")),
    )
    op.create_index(
        "CraftAlias_aliasNorm_trgm_idx",
        "CraftAlias",
        ["aliasNorm"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"aliasNorm": "gin_trgm_ops"},
    )
    op.create_index(op.f("CraftAlias_craftId_idx"), "CraftAlias", ["craftId"], unique=False)
    op.create_index(op.f("CraftAlias_status_idx"), "CraftAlias", ["status"], unique=False)
    op.create_table(
        "CraftLocation",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column(
            "precision",
            postgresql.ENUM("STATE", "DISTRICT", "POINT", name="LocationPrecision", create_type=False),
            nullable=False,
        ),
        sa.Column("stateLgd", sa.Integer(), nullable=True),
        sa.Column("districtLgd", sa.Integer(), nullable=True),
        sa.Column("geom", Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True),
        sa.Column("placeLabel", sa.String(length=300), nullable=True),
        sa.Column("sourceId", sa.UUID(), nullable=True),
        sa.Column(
            "evidenceLevel",
            postgresql.ENUM(
                "VERIFIED", "REVIEWED", "PROVISIONAL", "HYPOTHESIS", name="EvidenceLevel", create_type=False
            ),
            server_default="PROVISIONAL",
            nullable=False,
        ),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("CraftLocation_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["districtLgd"],
            ["AdminDistrict.lgd"],
            name=op.f("CraftLocation_districtLgd_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sourceId"], ["Source.id"], name=op.f("CraftLocation_sourceId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["stateLgd"], ["AdminState.lgd"], name=op.f("CraftLocation_stateLgd_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("CraftLocation_pkey")),
    )
    op.create_index(op.f("CraftLocation_craftId_idx"), "CraftLocation", ["craftId"], unique=False)
    op.create_index(op.f("CraftLocation_districtLgd_idx"), "CraftLocation", ["districtLgd"], unique=False)
    op.create_index(
        "CraftLocation_geom_gist_idx", "CraftLocation", ["geom"], unique=False, postgresql_using="gist"
    )
    op.create_index(op.f("CraftLocation_stateLgd_idx"), "CraftLocation", ["stateLgd"], unique=False)
    op.create_table(
        "EnrichmentJob",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("requestedById", sa.UUID(), nullable=True),
        sa.Column("mode", sa.String(length=40), server_default="T3", nullable=False),
        sa.Column("facets", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column(
            "budgetUsd", sa.Numeric(precision=10, scale=4), server_default=sa.text("2"), nullable=False
        ),
        sa.Column("spentUsd", sa.Numeric(precision=10, scale=4), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "QUEUED",
                "RUNNING",
                "SUCCEEDED",
                "FAILED",
                "BLOCKED",
                "CANCELLED",
                name="JobStatus",
                create_type=False,
            ),
            server_default="QUEUED",
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("startedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finishedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint('"budgetUsd" <= 10', name=op.f("EnrichmentJob_budget_max_check")),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("EnrichmentJob_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["requestedById"], ["User.id"], name=op.f("EnrichmentJob_requestedById_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("EnrichmentJob_pkey")),
    )
    op.create_index(
        op.f("EnrichmentJob_craftId_status_idx"), "EnrichmentJob", ["craftId", "status"], unique=False
    )
    op.create_table(
        "GiRegistration",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("giNo", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("goodsClass", sa.String(length=80), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("registeredOn", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("holder", sa.Text(), nullable=True),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("sourceId", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("GiRegistration_craftId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["sourceId"], ["Source.id"], name=op.f("GiRegistration_sourceId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("GiRegistration_pkey")),
        sa.UniqueConstraint("giNo", name=op.f("GiRegistration_giNo_key")),
    )
    op.create_index(op.f("GiRegistration_craftId_idx"), "GiRegistration", ["craftId"], unique=False)
    op.create_table(
        "Process",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("variant", sa.String(length=200), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("Process_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Process_pkey")),
    )
    op.create_index(op.f("Process_craftId_idx"), "Process", ["craftId"], unique=False)
    op.create_table(
        "Answer",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conversationId", sa.UUID(), nullable=True),
        sa.Column("userId", sa.UUID(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), server_default="en", nullable=False),
        sa.Column(
            "mode",
            postgresql.ENUM("VERIFIED", "HYBRID", "DEEP", name="AnswerMode", create_type=False),
            nullable=False,
        ),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("plan", postgresql.JSONB(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column(
            "claimIds", postgresql.ARRAY(sa.UUID()), server_default=sa.text("ARRAY[]::uuid[]"), nullable=False
        ),
        sa.Column(
            "liveCandidateIds",
            postgresql.ARRAY(sa.UUID()),
            server_default=sa.text("ARRAY[]::uuid[]"),
            nullable=False,
        ),
        sa.Column(
            "tiersUsed",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("ARRAY[]::text[]"),
            nullable=False,
        ),
        sa.Column("costUsd", sa.Numeric(precision=10, scale=6), server_default=sa.text("0"), nullable=False),
        sa.Column("latencyMs", sa.Integer(), nullable=True),
        sa.Column("route", postgresql.JSONB(), nullable=True),
        sa.Column("staleSince", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversationId"],
            ["Conversation.id"],
            name=op.f("Answer_conversationId_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("Answer_craftId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("Answer_userId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Answer_pkey")),
    )
    op.create_index(op.f("Answer_conversationId_idx"), "Answer", ["conversationId"], unique=False)
    op.create_index(op.f("Answer_craftId_idx"), "Answer", ["craftId"], unique=False)
    op.create_index(op.f("Answer_userId_createdAt_idx"), "Answer", ["userId", "createdAt"], unique=False)
    op.create_table(
        "ConceptEdge",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("srcId", sa.UUID(), nullable=False),
        sa.Column("dstId", sa.UUID(), nullable=False),
        sa.Column(
            "relation",
            postgresql.ENUM(
                "PRECEDES",
                "USES",
                "PRODUCES",
                "SCIENTIFICALLY_EXPLAINED_BY",
                "AFFECTED_BY",
                "PART_OF",
                "DEPENDS_ON",
                "CAUSES",
                "ENABLES",
                "EXPLAINS",
                "REQUIRES",
                "PRACTITIONER_EXPLAINS",
                "HAS_PROPERTY",
                "CONTRASTS_WITH",
                "ASSOCIATED_WITH",
                "SIMILAR_TO",
                "USED_FOR",
                "PREVENTS",
                "MODIFIES",
                name="ConceptRelation",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("sourceRelation", sa.String(length=80), nullable=True),
        sa.Column("claimId", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("ConceptEdge_claimId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["dstId"], ["Concept.id"], name=op.f("ConceptEdge_dstId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["srcId"], ["Concept.id"], name=op.f("ConceptEdge_srcId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ConceptEdge_pkey")),
        sa.UniqueConstraint("srcId", "dstId", "relation", name=op.f("ConceptEdge_srcId_dstId_relation_key")),
    )
    op.create_index(op.f("ConceptEdge_dstId_idx"), "ConceptEdge", ["dstId"], unique=False)
    op.create_table(
        "EnrichmentProposal",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("jobId", sa.UUID(), nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=False),
        sa.Column("dedupeOfClaimId", sa.UUID(), nullable=True),
        sa.Column("checks", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("EnrichmentProposal_claimId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["dedupeOfClaimId"],
            ["Claim.id"],
            name=op.f("EnrichmentProposal_dedupeOfClaimId_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["jobId"], ["EnrichmentJob.id"], name=op.f("EnrichmentProposal_jobId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("EnrichmentProposal_pkey")),
    )
    op.create_index(op.f("EnrichmentProposal_claimId_idx"), "EnrichmentProposal", ["claimId"], unique=False)
    op.create_index(op.f("EnrichmentProposal_jobId_idx"), "EnrichmentProposal", ["jobId"], unique=False)
    op.create_table(
        "Material",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("nameNorm", sa.String(length=300), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "FIBRE",
                "DYE",
                "MORDANT",
                "MINERAL",
                "CLAY",
                "METAL",
                "WOOD",
                "RESIN",
                "FUEL",
                "WATER",
                "OTHER",
                name="MaterialKind",
                create_type=False,
            ),
            server_default="OTHER",
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("conceptId", sa.UUID(), nullable=True),
        sa.Column("compoundId", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["compoundId"], ["Compound.id"], name=op.f("Material_compoundId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["conceptId"], ["Concept.id"], name=op.f("Material_conceptId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Material_pkey")),
        sa.UniqueConstraint("nameNorm", name=op.f("Material_nameNorm_key")),
    )
    op.create_table(
        "ProcessStage",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("processId", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("conceptId", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column(
            "stageType",
            postgresql.ENUM(
                "PREP",
                "SCOUR",
                "MORDANT",
                "DYE",
                "RESIST",
                "PRINT",
                "WASH",
                "DRY",
                "SHAPE",
                "CARVE",
                "FIRE",
                "CAST",
                "FINISH",
                "OTHER",
                name="StageType",
                create_type=False,
            ),
            server_default="OTHER",
            nullable=False,
        ),
        sa.Column("durationText", sa.String(length=200), nullable=True),
        sa.Column("tempMinC", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("tempMaxC", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("phMin", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("phMax", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("medium", sa.String(length=200), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conceptId"], ["Concept.id"], name=op.f("ProcessStage_conceptId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["processId"], ["Process.id"], name=op.f("ProcessStage_processId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("ProcessStage_pkey")),
        sa.UniqueConstraint("processId", "ordinal", name=op.f("ProcessStage_processId_ordinal_key")),
    )
    op.create_table(
        "VoiceSession",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("elConversationId", sa.String(length=120), nullable=True),
        sa.Column("agentId", sa.String(length=120), nullable=True),
        sa.Column("nonceHash", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=16), server_default="en", nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("conversationId", sa.UUID(), nullable=True),
        sa.Column(
            "mode",
            postgresql.ENUM("VERIFIED", "HYBRID", "DEEP", name="AnswerMode", create_type=False),
            server_default="HYBRID",
            nullable=False,
        ),
        sa.Column("startedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("endedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("turnCount", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("reservedSeconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("billedSeconds", sa.Integer(), nullable=True),
        sa.Column("transcriptEnc", sa.Text(), nullable=True),
        sa.Column("retentionUntil", sa.DateTime(timezone=True), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversationId"],
            ["Conversation.id"],
            name=op.f("VoiceSession_conversationId_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("VoiceSession_craftId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("VoiceSession_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("VoiceSession_pkey")),
        sa.UniqueConstraint("elConversationId", name=op.f("VoiceSession_elConversationId_key")),
    )
    op.create_index(
        "VoiceSession_one_live_per_user_key",
        "VoiceSession",
        ["userId"],
        unique=True,
        postgresql_where=sa.text('"endedAt" IS NULL'),
    )
    op.create_index(op.f("VoiceSession_retentionUntil_idx"), "VoiceSession", ["retentionUntil"], unique=False)
    op.create_index(
        op.f("VoiceSession_userId_endedAt_idx"), "VoiceSession", ["userId", "endedAt"], unique=False
    )
    op.create_table(
        "AnswerSentence",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("answerId", sa.UUID(), nullable=False),
        sa.Column("sectionOrdinal", sa.Integer(), nullable=False),
        sa.Column("sectionHeading", sa.String(length=300), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "evidenceLevel",
            postgresql.ENUM(
                "VERIFIED", "REVIEWED", "PROVISIONAL", "HYPOTHESIS", name="EvidenceLevel", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("translated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("openQuestion", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["answerId"], ["Answer.id"], name=op.f("AnswerSentence_answerId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("AnswerSentence_pkey")),
        sa.UniqueConstraint(
            "answerId",
            "sectionOrdinal",
            "ordinal",
            name=op.f("AnswerSentence_answerId_sectionOrdinal_ordinal_key"),
        ),
    )
    op.create_table(
        "AnswerTrace",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("answerId", sa.UUID(), nullable=False),
        sa.Column("step", sa.String(length=60), nullable=False),
        sa.Column("ordinal", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ms", sa.Integer(), nullable=True),
        sa.Column("detail", postgresql.JSONB(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["answerId"], ["Answer.id"], name=op.f("AnswerTrace_answerId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("AnswerTrace_pkey")),
    )
    op.create_index(
        op.f("AnswerTrace_answerId_ordinal_idx"), "AnswerTrace", ["answerId", "ordinal"], unique=False
    )
    op.create_table(
        "LiveCandidate",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("answerId", sa.UUID(), nullable=True),
        sa.Column("userId", sa.UUID(), nullable=True),
        sa.Column("tier", postgresql.ENUM("T3", "T4", name="LiveTier", create_type=False), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("webFetchId", sa.UUID(), nullable=True),
        sa.Column("sourceLabel", sa.String(length=300), nullable=True),
        sa.Column("quote", sa.String(length=300), nullable=False),
        sa.Column(
            "quoteCheck",
            postgresql.ENUM("PASS", "FAIL", "NA", name="QuoteCheck", create_type=False),
            server_default="NA",
            nullable=False,
        ),
        sa.Column("facet", sa.String(length=120), nullable=True),
        sa.Column("writtenBackClaimId", sa.UUID(), nullable=True),
        sa.Column(
            "expiresAt",
            sa.DateTime(timezone=True),
            server_default=sa.text("now() + interval '30 days'"),
            nullable=False,
        ),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["answerId"], ["Answer.id"], name=op.f("LiveCandidate_answerId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("LiveCandidate_userId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["webFetchId"], ["WebFetch.id"], name=op.f("LiveCandidate_webFetchId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["writtenBackClaimId"],
            ["Claim.id"],
            name=op.f("LiveCandidate_writtenBackClaimId_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("LiveCandidate_pkey")),
    )
    op.create_index(op.f("LiveCandidate_answerId_idx"), "LiveCandidate", ["answerId"], unique=False)
    op.create_index(op.f("LiveCandidate_expiresAt_idx"), "LiveCandidate", ["expiresAt"], unique=False)
    op.create_index(op.f("LiveCandidate_userId_idx"), "LiveCandidate", ["userId"], unique=False)
    op.create_table(
        "MediaJob",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "kind", postgresql.ENUM("IMAGE", "VIDEO", name="MediaKind", create_type=False), nullable=False
        ),
        sa.Column("requestedById", sa.UUID(), nullable=True),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("stageId", sa.UUID(), nullable=True),
        sa.Column(
            "claimIds", postgresql.ARRAY(sa.UUID()), server_default=sa.text("ARRAY[]::uuid[]"), nullable=False
        ),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("promptVersion", sa.String(length=40), nullable=True),
        sa.Column("promptHash", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("params", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "QUEUED",
                "RUNNING",
                "SUCCEEDED",
                "FAILED",
                "BLOCKED",
                "CANCELLED",
                name="JobStatus",
                create_type=False,
            ),
            server_default="QUEUED",
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("costUsd", sa.Numeric(precision=10, scale=6), server_default=sa.text("0"), nullable=False),
        sa.Column("billedTokens", sa.Integer(), nullable=True),
        sa.Column("idempotencyKey", sa.String(length=160), nullable=False),
        sa.Column("bundle", postgresql.JSONB(), nullable=True),
        sa.Column("providerRef", sa.String(length=300), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("MediaJob_craftId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["requestedById"], ["User.id"], name=op.f("MediaJob_requestedById_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["stageId"], ["ProcessStage.id"], name=op.f("MediaJob_stageId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("MediaJob_pkey")),
        sa.UniqueConstraint("idempotencyKey", name=op.f("MediaJob_idempotencyKey_key")),
    )
    op.create_index(op.f("MediaJob_promptHash_idx"), "MediaJob", ["promptHash"], unique=False)
    op.create_index(
        op.f("MediaJob_requestedById_createdAt_idx"), "MediaJob", ["requestedById", "createdAt"], unique=False
    )
    op.create_index(op.f("MediaJob_status_kind_idx"), "MediaJob", ["status", "kind"], unique=False)
    op.create_table(
        "Message",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("conversationId", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("USER", "ASSISTANT", "SYSTEM", name="MessageRole", create_type=False),
            nullable=False,
        ),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("answerId", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["answerId"], ["Answer.id"], name=op.f("Message_answerId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["conversationId"],
            ["Conversation.id"],
            name=op.f("Message_conversationId_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Message_pkey")),
    )
    op.create_index(
        op.f("Message_conversationId_createdAt_idx"), "Message", ["conversationId", "createdAt"], unique=False
    )
    op.create_table(
        "Reaction",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("stageId", sa.UUID(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "REDOX",
                "ACID_BASE",
                "COMPLEXATION",
                "PRECIPITATION",
                "DEHYDRATION",
                "DEHYDROXYLATION",
                "PHASE_CHANGE",
                "POLYMERISATION",
                "HYDROLYSIS",
                "OTHER",
                name="ReactionKind",
                create_type=False,
            ),
            server_default="OTHER",
            nullable=False,
        ),
        sa.Column("species", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("equationInput", sa.Text(), nullable=True),
        sa.Column("equationBalanced", sa.Text(), nullable=True),
        sa.Column("coefficients", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("balanced", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("conditions", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("checkerVersion", sa.String(length=40), nullable=True),
        sa.Column("deltaHKjMol", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["stageId"], ["ProcessStage.id"], name=op.f("Reaction_stageId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Reaction_pkey")),
    )
    op.create_index(op.f("Reaction_stageId_idx"), "Reaction", ["stageId"], unique=False)
    op.create_table(
        "StageMaterial",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("stageId", sa.UUID(), nullable=False),
        sa.Column("materialId", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "INPUT",
                "MORDANT",
                "DYE",
                "RESIST",
                "BINDER",
                "FLUX",
                "FUEL",
                "TOOL",
                "PRODUCT",
                "OTHER",
                name="MaterialRole",
                create_type=False,
            ),
            server_default="INPUT",
            nullable=False,
        ),
        sa.Column("quantityText", sa.String(length=200), nullable=True),
        sa.Column("claimId", sa.UUID(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("StageMaterial_claimId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["materialId"], ["Material.id"], name=op.f("StageMaterial_materialId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["stageId"], ["ProcessStage.id"], name=op.f("StageMaterial_stageId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("StageMaterial_pkey")),
        sa.UniqueConstraint(
            "stageId", "materialId", "role", name=op.f("StageMaterial_stageId_materialId_role_key")
        ),
    )
    op.create_index(op.f("StageMaterial_materialId_idx"), "StageMaterial", ["materialId"], unique=False)
    op.create_table(
        "AnswerCitation",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sentenceId", sa.UUID(), nullable=False),
        sa.Column("claimId", sa.UUID(), nullable=True),
        sa.Column("claimSourceId", sa.UUID(), nullable=True),
        sa.Column("liveCandidateId", sa.UUID(), nullable=True),
        sa.Column("sourceId", sa.UUID(), nullable=True),
        sa.Column("quote", sa.String(length=300), nullable=True),
        sa.Column("locator", sa.String(length=300), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("sourceLabel", sa.String(length=300), nullable=True),
        sa.Column("ordinal", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("AnswerCitation_claimId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["claimSourceId"],
            ["ClaimSource.id"],
            name=op.f("AnswerCitation_claimSourceId_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["liveCandidateId"],
            ["LiveCandidate.id"],
            name=op.f("AnswerCitation_liveCandidateId_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sentenceId"],
            ["AnswerSentence.id"],
            name=op.f("AnswerCitation_sentenceId_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sourceId"], ["Source.id"], name=op.f("AnswerCitation_sourceId_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("AnswerCitation_pkey")),
    )
    op.create_index(op.f("AnswerCitation_claimId_idx"), "AnswerCitation", ["claimId"], unique=False)
    op.create_index(op.f("AnswerCitation_sentenceId_idx"), "AnswerCitation", ["sentenceId"], unique=False)
    op.create_table(
        "MediaAsset",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("jobId", sa.UUID(), nullable=True),
        sa.Column("s3Key", sa.Text(), nullable=False),
        sa.Column("mime", sa.String(length=120), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("durationS", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("altText", sa.Text(), nullable=True),
        sa.Column(
            "visibility",
            postgresql.ENUM("PRIVATE", "CRAFT_SHARED", name="MediaVisibility", create_type=False),
            server_default="PRIVATE",
            nullable=False,
        ),
        sa.Column("approvedById", sa.UUID(), nullable=True),
        sa.Column("secondApprovedById", sa.UUID(), nullable=True),
        sa.Column("depictsNamedCluster", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["approvedById"], ["User.id"], name=op.f("MediaAsset_approvedById_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["jobId"], ["MediaJob.id"], name=op.f("MediaAsset_jobId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["secondApprovedById"],
            ["User.id"],
            name=op.f("MediaAsset_secondApprovedById_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("MediaAsset_pkey")),
        sa.UniqueConstraint("s3Key", name=op.f("MediaAsset_s3Key_key")),
    )
    op.create_index(op.f("MediaAsset_jobId_idx"), "MediaAsset", ["jobId"], unique=False)
    op.create_index(op.f("MediaAsset_visibility_idx"), "MediaAsset", ["visibility"], unique=False)
    op.create_table(
        "Objection",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("claimId", sa.UUID(), nullable=True),
        sa.Column("mediaAssetId", sa.UUID(), nullable=True),
        sa.Column("answerId", sa.UUID(), nullable=True),
        sa.Column("raisedById", sa.UUID(), nullable=True),
        sa.Column("contactEmail", sa.String(length=320), nullable=True),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "FACTUAL",
                "ATTRIBUTION",
                "SACRED_OR_RESTRICTED",
                "DEPICTION",
                "OTHER",
                name="ObjectionKind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "OPEN", "ACKNOWLEDGED", "UPHELD", "DISMISSED", name="ObjectionStatus", create_type=False
            ),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("ackDueAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decideDueAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decidedById", sa.UUID(), nullable=True),
        sa.Column("decidedAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decisionNote", sa.Text(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["answerId"], ["Answer.id"], name=op.f("Objection_answerId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["claimId"], ["Claim.id"], name=op.f("Objection_claimId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("Objection_craftId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["decidedById"], ["User.id"], name=op.f("Objection_decidedById_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["mediaAssetId"], ["MediaAsset.id"], name=op.f("Objection_mediaAssetId_fkey"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["raisedById"], ["User.id"], name=op.f("Objection_raisedById_fkey"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("Objection_pkey")),
    )
    op.create_index(op.f("Objection_craftId_idx"), "Objection", ["craftId"], unique=False)
    op.create_index(op.f("Objection_status_idx"), "Objection", ["status"], unique=False)
    op.create_table(
        "SavedItem",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("answerId", sa.UUID(), nullable=True),
        sa.Column("craftId", sa.UUID(), nullable=True),
        sa.Column("mediaAssetId", sa.UUID(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["answerId"], ["Answer.id"], name=op.f("SavedItem_answerId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("SavedItem_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["mediaAssetId"], ["MediaAsset.id"], name=op.f("SavedItem_mediaAssetId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("SavedItem_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("SavedItem_pkey")),
    )
    op.create_index(
        op.f("SavedItem_userId_createdAt_idx"), "SavedItem", ["userId", "createdAt"], unique=False
    )
    op.create_table(
        "UserPreference",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("userId", sa.UUID(), nullable=False),
        sa.Column("theme", sa.String(length=16), server_default="system", nullable=False),
        sa.Column("reducedMotion", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("largerText", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("highContrast", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["userId"], ["User.id"], name=op.f("UserPreference_userId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("UserPreference_pkey")),
        sa.UniqueConstraint("userId", name=op.f("UserPreference_userId_key")),
    )


def _create_enums() -> None:
    bind = op.get_bind()
    for name, values in ENUMS:
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)


REFUSE_MUTATION_FUNCTION = """
CREATE OR REPLACE FUNCTION kv_refuse_mutation() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME USING ERRCODE = 'insufficient_privilege';
END;
$fn$
"""

REVOKE_PUBLIC_ROLES = """
DO $do$
DECLARE grantee text;
BEGIN
    FOREACH grantee IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = grantee) THEN
            EXECUTE format('REVOKE ALL ON %s FROM %I', :tables, grantee);
        END IF;
    END LOOP;
END
$do$
"""


def _harden() -> None:
    op.execute(REFUSE_MUTATION_FUNCTION)
    for table in APPEND_ONLY_TABLES:
        op.execute(
            f'CREATE TRIGGER "{table}_append_only" BEFORE UPDATE OR DELETE ON "{table}" '
            "FOR EACH ROW EXECUTE FUNCTION kv_refuse_mutation()"
        )
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    quoted = ", ".join(f'"{table}"' for table in TABLES)
    op.execute(REVOKE_PUBLIC_ROLES.replace(":tables", "'" + quoted.replace("'", "''") + "'"))


def _seed() -> None:
    for row in PROVIDERS:
        op.execute(
            sa.text(
                'INSERT INTO "Provider" (name, preset, kind, "baseUrl", "apiKeySecretKey", "dataClass", '
                '"maxConcurrency") VALUES (CAST(:name AS "AiProvider"), :preset, :kind, :baseUrl, '
                ':apiKeySecretKey, CAST(:dataClass AS "ProviderDataClass"), :maxConcurrency)'
            ).bindparams(**row)
        )
    for row in ROUTES:
        op.execute(
            sa.text(
                'INSERT INTO "RoutePolicy" (task, ordinal, "providerId", model) '
                'SELECT CAST(:task AS "AiTask"), :ordinal, p.id, :model FROM "Provider" p '
                'WHERE p.name = CAST(:provider AS "AiProvider")'
            ).bindparams(**row)
        )
    for key, value in APP_SETTINGS.items():
        op.execute(
            sa.text('INSERT INTO "AppSetting" (key, value) VALUES (:key, CAST(:value AS jsonb))').bindparams(
                key=key, value=json.dumps(value)
            )
        )
    for row in QUOTAS:
        op.execute(
            sa.text(
                'INSERT INTO "QuotaPolicy" (role, resource, "perDay") '
                'VALUES (CAST(:role AS "UserRole"), CAST(:resource AS "QuotaResource"), :perDay)'
            ).bindparams(**row)
        )


def upgrade() -> None:
    for extension in EXTENSIONS:
        op.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')
    _create_enums()
    _create_tables()
    _harden()
    _seed()


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
    op.execute("DROP FUNCTION IF EXISTS kv_refuse_mutation()")
    for name, _values in reversed(ENUMS):
        op.execute(f'DROP TYPE IF EXISTS "{name}"')
