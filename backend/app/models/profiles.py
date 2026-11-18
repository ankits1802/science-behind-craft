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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, one_of, updated_at
from app.models.enums import AGE_BANDS, CREDIT_MODES, GENDERS

CREDIT_NAME_CHECK = '"creditMode" <> \'FULL_NAME\' OR "creditName" IS NOT NULL'
CREDIT_SHORT_NAME_CHECK = '"creditMode" <> \'FIRST_NAME\' OR "creditShortName" IS NOT NULL'


class StudentProfile(Base):
    __tablename__ = "StudentProfile"

    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="CASCADE"), primary_key=True
    )
    ageBand: Mapped[str] = mapped_column(String(16), nullable=False)
    gender: Mapped[str] = mapped_column(String(16), nullable=False)
    completedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("ageBand", AGE_BANDS), name="ageBand"),
        CheckConstraint(one_of("gender", GENDERS), name="gender"),
    )


class ArtisanProfile(Base):
    __tablename__ = "ArtisanProfile"

    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="CASCADE"), primary_key=True
    )
    districtLgd: Mapped[int] = mapped_column(
        Integer, ForeignKey("AdminDistrict.lgd", ondelete="RESTRICT"), nullable=False
    )
    spokenLanguage: Mapped[str] = mapped_column(String(16), nullable=False)
    creditMode: Mapped[str] = mapped_column(String(24), nullable=False)
    creditName: Mapped[str | None] = mapped_column(String(120))
    creditShortName: Mapped[str | None] = mapped_column(String(60))
    adultConfirmedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("creditMode", CREDIT_MODES), name="creditMode"),
        CheckConstraint(CREDIT_NAME_CHECK, name="creditName"),
        CheckConstraint(CREDIT_SHORT_NAME_CHECK, name="creditShortName"),
        Index(None, "districtLgd"),
    )


class ArtisanCraft(Base):
    __tablename__ = "ArtisanCraft"

    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="CASCADE"), primary_key=True
    )
    craftId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Craft.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("userId", "position"),
        CheckConstraint('"position" >= 1', name="position"),
        Index(None, "craftId"),
    )
