import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text as sql_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, created_at, one_of, updated_at

__all__ = ["FETCH_OUTCOMES", "PROBLEM_COLUMN_CHARS", "SourceUpkeep"]

FETCH_OUTCOMES = ("FETCHED", "REFUSED", "FAILED")
OUTCOME_COLUMN_CHARS = 16
PROBLEM_COLUMN_CHARS = 300


class SourceUpkeep(Base):
    __tablename__ = "SourceUpkeep"

    sourceId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Source.id", ondelete="CASCADE"), primary_key=True
    )
    checkedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome: Mapped[str] = mapped_column(String(OUTCOME_COLUMN_CHARS), nullable=False)
    failures: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sql_text("0"))
    problem: Mapped[str | None] = mapped_column(String(PROBLEM_COLUMN_CHARS))
    archiveTriedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archivedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archiveUrl: Mapped[str | None] = mapped_column(Text)
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("outcome", FETCH_OUTCOMES), name="outcome"),
        CheckConstraint('"failures" >= 0', name="failures"),
        CheckConstraint('("archivedAt" IS NULL) = ("archiveUrl" IS NULL)', name="archived"),
        CheckConstraint('"archivedAt" IS NULL OR "archiveTriedAt" IS NOT NULL', name="archive_tried"),
        Index(None, "checkedAt"),
    )
