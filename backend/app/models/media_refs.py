import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, one_of, updated_at, uuid_pk
from app.models.enums import IMAGE_RELEVANCE, MEDIA_DISPLAYS

MEDIA_TEXT_COLUMN_CHARS = 300
PICTURE_VERDICTS = ("SHOWS", "DOES_NOT_SHOW")
CHECK_REASON_MIN_CHARS = 12
CHECK_REASON_MAX_CHARS = 300
CONTRIBUTOR_CHECK = 'NOT "ruling"'


class MediaRef(Base):
    __tablename__ = "MediaRef"

    id: Mapped[uuid.UUID] = uuid_pk()
    urlKey: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    pageUrl: Mapped[str] = mapped_column(Text, nullable=False)
    imageUrl: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(MEDIA_TEXT_COLUMN_CHARS), nullable=False)
    alt: Mapped[str] = mapped_column(String(MEDIA_TEXT_COLUMN_CHARS), nullable=False)
    author: Mapped[str | None] = mapped_column(String(MEDIA_TEXT_COLUMN_CHARS))
    site: Mapped[str] = mapped_column(String(MEDIA_TEXT_COLUMN_CHARS), nullable=False)
    credit: Mapped[str | None] = mapped_column(String(MEDIA_TEXT_COLUMN_CHARS))
    licence: Mapped[str | None] = mapped_column(String(200))
    licenceUrl: Mapped[str | None] = mapped_column(Text)
    sourceId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Source.id", ondelete="SET NULL")
    )
    objectKey: Mapped[str | None] = mapped_column(Text)
    retrievedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("display", MEDIA_DISPLAYS), name="display"),
        CheckConstraint("num_nonnulls(width, height) <> 1", name="size"),
        Index(None, "sourceId"),
    )


class MediaRefClaim(Base):
    __tablename__ = "MediaRefClaim"

    mediaRefId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("MediaRef.id", ondelete="CASCADE"), primary_key=True
    )
    claimId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Claim.id", ondelete="CASCADE"), primary_key=True
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, server_default=text("gen_random_uuid()")
    )
    relevance: Mapped[str] = mapped_column(String(16), nullable=False)
    refusedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (
        CheckConstraint(one_of("relevance", IMAGE_RELEVANCE), name="relevance"),
        Index(None, "claimId"),
    )


class PictureCheck(Base):
    __tablename__ = "PictureCheck"

    id: Mapped[uuid.UUID] = uuid_pk()
    linkId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("MediaRefClaim.id", ondelete="CASCADE"), nullable=False
    )
    userId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(CHECK_REASON_MAX_CHARS))
    ruling: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (
        CheckConstraint(one_of("verdict", PICTURE_VERDICTS), name="verdict"),
        CheckConstraint(
            f'"ruling" OR char_length("reason") BETWEEN {CHECK_REASON_MIN_CHARS} AND {CHECK_REASON_MAX_CHARS}',
            name="reason",
        ),
        Index(
            "PictureCheck_linkId_userId_once_key",
            "linkId",
            "userId",
            unique=True,
            postgresql_where=text(CONTRIBUTOR_CHECK),
        ),
        Index(None, "linkId", "createdAt"),
        Index(None, "userId", "createdAt"),
    )
