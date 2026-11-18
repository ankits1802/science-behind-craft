from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_field_voices"
down_revision: str | Sequence[str] | None = "0026_curated_categories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SIGNED_IN = "SIGNED_IN"
ENUM_ADDITIONS: tuple[tuple[str, tuple[str, ...]], ...] = (("ChunkAcl", ("SIGNED_IN",)),)
CHUNK_ACLS_BEFORE = ("PUBLIC", "RESEARCHER")
NEW_TABLES = (
    "FieldVoiceStream",
    "FieldRecording",
    "FieldSegment",
    "FieldRecordingCraft",
    "FieldImage",
    "FieldImageCraft",
)
PORTALS = ("DESIGNER", "FIELD_REPOSITORY")
STREAMS = ("TRANSCRIPTS", "IMAGES")
MEDIA_TYPES = ("AUDIO", "VIDEO")
TRANSCRIPT_SOURCES = ("TURNS", "TEXT", "TYPED")
TEXT_SOURCES = ("MACHINE", "EDITED", "TYPED")
ENGLISH_SOURCES = ("ORIGINAL", "MACHINE", "EDITED")
SEGMENT_ROLES = ("ARTISAN", "DESIGNER", "RESEARCHER", "OTHER")
IMAGE_TYPES = ("image/jpeg", "image/png")
SHA256 = "~ '^[0-9a-f]{64}$'"
JSONB = postgresql.JSONB(astext_type=sa.Text())
LANGUAGES = postgresql.ARRAY(sa.String(length=16))
STAMP = sa.DateTime(timezone=True)
NOW = sa.text("now()")
EMPTY_LIST = sa.text("'[]'::jsonb")
EMPTY_OBJECT = sa.text("'{}'::jsonb")
NO_LANGUAGES = sa.text("ARRAY[]::varchar[]")
NEW_ID = sa.text("gen_random_uuid()")

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


def _check_one_of(table: str, column: str, values: Sequence[str]) -> None:
    op.create_check_constraint(op.f(f"{table}_{column}_check"), table, f'"{column}" IN ({_listed(values)})')


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for enum_name, values in ENUM_ADDITIONS:
            for value in values:
                op.execute(f"ALTER TYPE \"{enum_name}\" ADD VALUE IF NOT EXISTS '{value}'")
    op.add_column("MediaRef", sa.Column("objectKey", sa.Text(), nullable=True))
    _create_streams()
    _create_recordings()
    _create_segments()
    _create_craft_links()
    _create_images()
    _create_image_crafts()
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(REVOKE_PUBLIC_ROLES.replace("{table}", table))


def downgrade() -> None:
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
    op.drop_column("MediaRef", "objectKey")
    op.execute(f"DELETE FROM \"Chunk\" WHERE acl::text = '{SIGNED_IN}'")
    op.execute('ALTER TYPE "ChunkAcl" RENAME TO "ChunkAcl_before_0027"')
    op.execute(f'CREATE TYPE "ChunkAcl" AS ENUM ({_listed(CHUNK_ACLS_BEFORE)})')
    op.execute('ALTER TABLE "Chunk" ALTER COLUMN acl DROP DEFAULT')
    op.execute('ALTER TABLE "Chunk" ALTER COLUMN acl TYPE "ChunkAcl" USING acl::text::"ChunkAcl"')
    op.execute("ALTER TABLE \"Chunk\" ALTER COLUMN acl SET DEFAULT 'PUBLIC'")
    op.execute('DROP TYPE "ChunkAcl_before_0027"')


def _create_streams() -> None:
    table = "FieldVoiceStream"
    op.create_table(
        "FieldVoiceStream",
        sa.Column("portal", sa.String(length=20), nullable=False),
        sa.Column("stream", sa.String(length=12), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("goneCursor", sa.Text(), nullable=True),
        sa.Column("rereadFrom", STAMP, nullable=True),
        sa.Column("lastContactAt", STAMP, nullable=True),
        sa.Column("lastCaughtUpAt", STAMP, nullable=True),
        sa.Column("lastReconciledAt", STAMP, nullable=True),
        sa.Column("live", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=True),
        sa.Column("createdAt", STAMP, server_default=NOW, nullable=False),
        sa.Column("updatedAt", STAMP, server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("portal", "stream", name=op.f("FieldVoiceStream_pkey")),
    )
    _check_one_of(table, "portal", PORTALS)
    _check_one_of(table, "stream", STREAMS)


def _create_recordings() -> None:
    op.create_table(
        "FieldRecording",
        sa.Column("id", sa.UUID(), server_default=NEW_ID, nullable=False),
        sa.Column("portal", sa.String(length=20), nullable=False),
        sa.Column("portalMediaId", sa.String(length=64), nullable=False),
        sa.Column("portalRecordingId", sa.String(length=64), nullable=True),
        sa.Column("revision", sa.String(length=32), nullable=False),
        sa.Column("portalUpdatedAt", STAMP, nullable=False),
        sa.Column("seenAt", STAMP, nullable=False),
        sa.Column("mediaType", sa.String(length=8), nullable=False),
        sa.Column("recordedAt", STAMP, nullable=False),
        sa.Column("durationMs", sa.Integer(), nullable=True),
        sa.Column("context", JSONB, server_default=EMPTY_OBJECT, nullable=False),
        sa.Column("people", JSONB, server_default=EMPTY_LIST, nullable=False),
        sa.Column("speakers", JSONB, server_default=EMPTY_LIST, nullable=False),
        sa.Column("transcriptSource", sa.String(length=8), nullable=False),
        sa.Column("languages", LANGUAGES, server_default=NO_LANGUAGES, nullable=False),
        sa.Column("english", JSONB, nullable=True),
        sa.Column("scrubbing", JSONB, server_default=EMPTY_OBJECT, nullable=False),
        sa.Column("unresolvedCrafts", JSONB, server_default=EMPTY_LIST, nullable=False),
        sa.Column("sourceId", sa.UUID(), nullable=False),
        sa.Column("hiddenAt", STAMP, nullable=True),
        sa.Column("createdAt", STAMP, server_default=NOW, nullable=False),
        sa.Column("updatedAt", STAMP, server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("FieldRecording_pkey")),
    )
    _constrain_recordings()


def _constrain_recordings() -> None:
    table = "FieldRecording"
    _check_one_of(table, "portal", PORTALS)
    _check_one_of(table, "mediaType", MEDIA_TYPES)
    _check_one_of(table, "transcriptSource", TRANSCRIPT_SOURCES)
    op.create_check_constraint(
        op.f(f"{table}_durationMs_check"), table, '"durationMs" IS NULL OR "durationMs" >= 1'
    )
    op.create_foreign_key(
        op.f(f"{table}_sourceId_fkey"), table, "Source", ["sourceId"], ["id"], ondelete="CASCADE"
    )
    op.create_unique_constraint(op.f(f"{table}_portal_portalMediaId_key"), table, ["portal", "portalMediaId"])
    op.create_unique_constraint(op.f(f"{table}_sourceId_key"), table, ["sourceId"])
    op.create_index(op.f(f"{table}_portal_hiddenAt_idx"), table, ["portal", "hiddenAt"])
    op.create_index(op.f(f"{table}_recordedAt_idx"), table, ["recordedAt"])


def _create_segments() -> None:
    op.create_table(
        "FieldSegment",
        sa.Column("id", sa.UUID(), server_default=NEW_ID, nullable=False),
        sa.Column("recordingId", sa.UUID(), nullable=False),
        sa.Column("portalSegmentId", sa.String(length=96), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("speakerKey", sa.String(length=40), nullable=True),
        sa.Column("personId", sa.String(length=64), nullable=True),
        sa.Column("role", sa.String(length=12), nullable=True),
        sa.Column("startMs", sa.Integer(), nullable=True),
        sa.Column("endMs", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("textSource", sa.String(length=8), nullable=False),
        sa.Column("english", sa.Text(), nullable=True),
        sa.Column("englishSource", sa.String(length=8), nullable=True),
        sa.Column("quotable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("FieldSegment_pkey")),
    )
    _constrain_segments()


def _constrain_segments() -> None:
    table = "FieldSegment"
    _check_one_of(table, "textSource", TEXT_SOURCES)
    checks = {
        "englishSource": f'"englishSource" IS NULL OR "englishSource" IN ({_listed(ENGLISH_SOURCES)})',
        "role": f'"role" IS NULL OR "role" IN ({_listed(SEGMENT_ROLES)})',
        "timed": 'num_nonnulls("startMs", "endMs") <> 1',
        "span": '"startMs" IS NULL OR "endMs" > "startMs"',
    }
    for name, condition in checks.items():
        op.create_check_constraint(op.f(f"{table}_{name}_check"), table, condition)
    op.create_foreign_key(
        op.f(f"{table}_recordingId_fkey"),
        table,
        "FieldRecording",
        ["recordingId"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        op.f(f"{table}_recordingId_portalSegmentId_key"), table, ["recordingId", "portalSegmentId"]
    )
    op.create_index(op.f(f"{table}_recordingId_position_idx"), table, ["recordingId", "position"])
    op.create_index(op.f(f"{table}_recordingId_quotable_idx"), table, ["recordingId", "quotable"])


def _create_craft_links() -> None:
    op.create_table(
        "FieldRecordingCraft",
        sa.Column("recordingId", sa.UUID(), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recordingId"],
            ["FieldRecording.id"],
            name=op.f("FieldRecordingCraft_recordingId_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("FieldRecordingCraft_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("recordingId", "craftId", name=op.f("FieldRecordingCraft_pkey")),
    )
    op.create_index(op.f("FieldRecordingCraft_craftId_idx"), "FieldRecordingCraft", ["craftId"])


def _create_image_crafts() -> None:
    op.create_table(
        "FieldImageCraft",
        sa.Column("imageId", sa.UUID(), nullable=False),
        sa.Column("craftId", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["imageId"], ["FieldImage.id"], name=op.f("FieldImageCraft_imageId_fkey"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["craftId"], ["Craft.id"], name=op.f("FieldImageCraft_craftId_fkey"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("imageId", "craftId", name=op.f("FieldImageCraft_pkey")),
    )
    op.create_index(op.f("FieldImageCraft_craftId_idx"), "FieldImageCraft", ["craftId"])


def _create_images() -> None:
    op.create_table(
        "FieldImage",
        sa.Column("id", sa.UUID(), server_default=NEW_ID, nullable=False),
        sa.Column("portal", sa.String(length=20), nullable=False),
        sa.Column("portalMediaId", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.String(length=32), nullable=False),
        sa.Column("portalUpdatedAt", STAMP, nullable=False),
        sa.Column("seenAt", STAMP, nullable=False),
        sa.Column("takenAt", STAMP, nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("belongsTo", JSONB, server_default=EMPTY_LIST, nullable=False),
        sa.Column("context", JSONB, server_default=EMPTY_OBJECT, nullable=False),
        sa.Column("people", JSONB, server_default=EMPTY_LIST, nullable=False),
        sa.Column("credits", JSONB, server_default=EMPTY_LIST, nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("rightsHolder", sa.String(length=200), nullable=False),
        sa.Column("licence", sa.String(length=200), nullable=True),
        sa.Column("portalSha256", sa.String(length=64), nullable=False),
        sa.Column("objectKey", sa.Text(), nullable=False),
        sa.Column("mimeType", sa.String(length=16), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("unresolvedCrafts", JSONB, server_default=EMPTY_LIST, nullable=False),
        sa.Column("mediaRefId", sa.UUID(), nullable=True),
        sa.Column("artisanLinked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("hiddenAt", STAMP, nullable=True),
        sa.Column("createdAt", STAMP, server_default=NOW, nullable=False),
        sa.Column("updatedAt", STAMP, server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("FieldImage_pkey")),
    )
    _constrain_images()


def _constrain_images() -> None:
    table = "FieldImage"
    _check_one_of(table, "portal", PORTALS)
    _check_one_of(table, "mimeType", IMAGE_TYPES)
    checks = {
        "sha256": f'"sha256" {SHA256}',
        "portalSha256": f'"portalSha256" {SHA256}',
        "size": '"width" >= 1 AND "height" >= 1 AND "bytes" >= 1',
    }
    for name, condition in checks.items():
        op.create_check_constraint(op.f(f"{table}_{name}_check"), table, condition)
    op.create_foreign_key(
        op.f(f"{table}_mediaRefId_fkey"), table, "MediaRef", ["mediaRefId"], ["id"], ondelete="SET NULL"
    )
    op.create_unique_constraint(op.f(f"{table}_portal_portalMediaId_key"), table, ["portal", "portalMediaId"])
    op.create_index(op.f(f"{table}_objectKey_idx"), table, ["objectKey"])
    op.create_index(op.f(f"{table}_portal_hiddenAt_idx"), table, ["portal", "hiddenAt"])
    op.create_index(op.f(f"{table}_mediaRefId_idx"), table, ["mediaRefId"])
    op.create_index(op.f(f"{table}_artisanLinked_idx"), table, ["artisanLinked"])
