import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at, one_of
from .enums import OPEN_PICTURE_SITES

__all__ = [
    "OPEN_AUTHOR_CHARS",
    "OPEN_CREDIT_CHARS",
    "OPEN_LICENCE_CHARS",
    "OPEN_TITLE_CHARS",
    "OpenPicture",
]

SITE_CHARS = 16
OPEN_TITLE_CHARS = 300
OPEN_AUTHOR_CHARS = 200
OPEN_LICENCE_CHARS = 200
OPEN_CREDIT_CHARS = 500


class OpenPicture(Base):
    __tablename__ = "OpenPicture"

    contributionId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ImageContribution.id", ondelete="CASCADE"), primary_key=True
    )
    site: Mapped[str] = mapped_column(String(SITE_CHARS), nullable=False)
    pageUrl: Mapped[str] = mapped_column(Text, nullable=False)
    fileUrl: Mapped[str] = mapped_column(Text, nullable=False)
    recordUrl: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(OPEN_TITLE_CHARS), nullable=False)
    author: Mapped[str] = mapped_column(String(OPEN_AUTHOR_CHARS), nullable=False)
    licence: Mapped[str] = mapped_column(String(OPEN_LICENCE_CHARS), nullable=False)
    licenceUrl: Mapped[str | None] = mapped_column(Text)
    credit: Mapped[str] = mapped_column(String(OPEN_CREDIT_CHARS), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    readAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (
        CheckConstraint(one_of("site", OPEN_PICTURE_SITES), name="site"),
        Index(None, "pageUrl"),
    )
