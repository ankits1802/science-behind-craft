import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, one_of, updated_at, uuid_pk
from app.models.enums import (
    CONTRIBUTION_STATUSES,
    DISCIPLINES,
    EXTRACTION_STATUSES,
    LOCATOR_PRECISIONS,
    TESTIMONY_CONCEPT_TYPES,
    TESTIMONY_ENGLISH_SOURCES,
    TESTIMONY_REJECT_REASONS,
    VOICE_TRANSPORTS,
)

UNFINISHED_EXTRACTION = "\"extractionStatus\" NOT IN ('DONE', 'NONE')"
APPROVED_CHECK = 'status <> \'APPROVED\' OR ("claimId" IS NOT NULL AND "approvedAt" IS NOT NULL)'
REJECTED_CHECK = 'status <> \'REJECTED\' OR ("rejectReason" IS NOT NULL AND "rejectedAt" IS NOT NULL)'
WITHDRAWN_CHECK = "status <> 'WITHDRAWN' OR \"withdrawnAt\" IS NOT NULL"
TEXTS_CLEARED_CHECK = (
    "\"textsClearedAt\" IS NULL OR (status IN ('REJECTED', 'WITHDRAWN') "
    'AND quote IS NULL AND english IS NULL AND "claimText" IS NULL)'
)


class ArtisanConversation(Base):
    __tablename__ = "ArtisanConversation"

    id: Mapped[uuid.UUID] = uuid_pk()
    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    voiceSessionId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("VoiceSession.id", ondelete="SET NULL"), unique=True
    )
    craftId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Craft.id", ondelete="RESTRICT"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    transport: Mapped[str] = mapped_column(String(16), nullable=False)
    consentRecordId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ConsentRecord.id", ondelete="SET NULL")
    )
    consentVersion: Mapped[str] = mapped_column(String(40), nullable=False)
    startedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    endedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transcriptEnc: Mapped[str | None] = mapped_column(Text)
    topicsAsked: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=sql_text("ARRAY[]::text[]")
    )
    extractionStatus: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")
    extractionAttempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=sql_text("0")
    )
    extractedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sourceId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Source.id", ondelete="SET NULL")
    )
    retentionUntil: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("transport", VOICE_TRANSPORTS), name="transport"),
        CheckConstraint(one_of("extractionStatus", EXTRACTION_STATUSES), name="extractionStatus"),
        Index(None, "userId", "startedAt"),
        Index(None, "craftId"),
        Index(None, "retentionUntil"),
        Index(None, "consentRecordId"),
        Index(None, "sourceId"),
        Index(
            "ArtisanConversation_extraction_unfinished_idx",
            "extractionStatus",
            postgresql_where=sql_text(UNFINISHED_EXTRACTION),
        ),
    )


class ArtisanConversationAudio(Base):
    __tablename__ = "ArtisanConversationAudio"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversationId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ArtisanConversation.id", ondelete="CASCADE"), nullable=False
    )
    turnId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    objectKey: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mimeType: Mapped[str] = mapped_column(String(80), nullable=False)
    bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    durationMs: Mapped[int] = mapped_column(Integer, nullable=False)
    startMs: Mapped[int] = mapped_column(Integer, nullable=False)
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (UniqueConstraint("conversationId", "turnId"),)


class ArtisanContribution(Base):
    __tablename__ = "ArtisanContribution"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversationId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ArtisanConversation.id", ondelete="RESTRICT"), nullable=False
    )
    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    craftId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Craft.id", ondelete="RESTRICT"), nullable=False
    )
    turnId: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")
    quote: Mapped[str | None] = mapped_column(String(300))
    quoteLanguage: Mapped[str] = mapped_column(String(16), nullable=False)
    english: Mapped[str | None] = mapped_column(String(600))
    englishSource: Mapped[str] = mapped_column(String(16), nullable=False)
    claimText: Mapped[str | None] = mapped_column(String(300))
    discipline: Mapped[str] = mapped_column(String(16), nullable=False)
    conceptType: Mapped[str] = mapped_column(String(40), nullable=False)
    conceptName: Mapped[str] = mapped_column(String(120), nullable=False)
    startMs: Mapped[int] = mapped_column(Integer, nullable=False)
    endMs: Mapped[int] = mapped_column(Integer, nullable=False)
    locatorPrecision: Mapped[str] = mapped_column(String(8), nullable=False)
    screens: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=sql_text("'{}'"))
    claimId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Claim.id", ondelete="SET NULL")
    )
    corroboratingClaimIds: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default=sql_text("'{}'")
    )
    reviewedById: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    reviewedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approvedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejectedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawnAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejectReason: Mapped[str | None] = mapped_column(String(32))
    reviewNote: Mapped[str | None] = mapped_column(String(500))
    textsClearedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("1"))
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("status", CONTRIBUTION_STATUSES), name="status"),
        CheckConstraint(one_of("englishSource", TESTIMONY_ENGLISH_SOURCES), name="englishSource"),
        CheckConstraint(one_of("discipline", DISCIPLINES), name="discipline"),
        CheckConstraint(one_of("conceptType", TESTIMONY_CONCEPT_TYPES), name="conceptType"),
        CheckConstraint(one_of("locatorPrecision", LOCATOR_PRECISIONS), name="locatorPrecision"),
        CheckConstraint(
            '"rejectReason" IS NULL OR ' + one_of("rejectReason", TESTIMONY_REJECT_REASONS),
            name="rejectReason",
        ),
        CheckConstraint('"endMs" > "startMs"', name="span"),
        CheckConstraint('cardinality("corroboratingClaimIds") <= 5', name="corroboratingClaimIds"),
        CheckConstraint(APPROVED_CHECK, name="approved"),
        CheckConstraint(REJECTED_CHECK, name="rejected"),
        CheckConstraint(WITHDRAWN_CHECK, name="withdrawn"),
        CheckConstraint(TEXTS_CLEARED_CHECK, name="textsCleared"),
        Index(None, "status", "createdAt"),
        Index(None, "craftId", "status"),
        Index(None, "userId", "createdAt"),
        Index(None, "conversationId"),
        Index(None, "claimId"),
        Index(None, "reviewedById"),
    )
