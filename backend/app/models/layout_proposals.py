import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, one_of, updated_at, uuid_pk

__all__ = [
    "LAYOUT_PROPOSAL_ORIGINS",
    "LAYOUT_PROPOSAL_STATUSES",
    "LAYOUT_PROPOSAL_SUBJECTS",
    "LAYOUT_REVIEW_NOTE_CHARS",
    "LayoutProposal",
]

LAYOUT_PROPOSAL_STATUSES = ("PENDING", "APPROVED", "REJECTED")
LAYOUT_PROPOSAL_ORIGINS = ("CONTRIBUTION", "AGENT")
LAYOUT_PROPOSAL_SUBJECTS = ("craft", "family", "category")
LAYOUT_REVIEW_NOTE_CHARS = 500
STATUS_CHARS = 16


def _person() -> Mapped[uuid.UUID | None]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL"))


class LayoutProposal(Base):
    __tablename__ = "LayoutProposal"

    id: Mapped[uuid.UUID] = uuid_pk()
    proposerId: Mapped[uuid.UUID | None] = _person()
    subjectKind: Mapped[str] = mapped_column(String(STATUS_CHARS), nullable=False)
    craftId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Craft.id", ondelete="CASCADE")
    )
    categoryId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("CraftCategory.id", ondelete="CASCADE")
    )
    baseVersion: Mapped[int] = mapped_column(Integer, nullable=False)
    entries: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    note: Mapped[str | None] = mapped_column(String(LAYOUT_REVIEW_NOTE_CHARS))
    critique: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    origin: Mapped[str] = mapped_column(String(STATUS_CHARS), nullable=False)
    status: Mapped[str] = mapped_column(String(STATUS_CHARS), nullable=False, server_default="PENDING")
    reviewedById: Mapped[uuid.UUID | None] = _person()
    reviewedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewNote: Mapped[str | None] = mapped_column(String(LAYOUT_REVIEW_NOTE_CHARS))
    layoutVersion: Mapped[int | None] = mapped_column(Integer)
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("status", LAYOUT_PROPOSAL_STATUSES), name="status"),
        CheckConstraint(one_of("origin", LAYOUT_PROPOSAL_ORIGINS), name="origin"),
        CheckConstraint(one_of("subjectKind", LAYOUT_PROPOSAL_SUBJECTS), name="subject_kind"),
        CheckConstraint('("craftId" IS NULL) <> ("categoryId" IS NULL)', name="one_subject"),
        CheckConstraint(
            '("subjectKind" = \'category\') = ("categoryId" IS NOT NULL)', name="subject_matches_kind"
        ),
        CheckConstraint('"baseVersion" >= 0', name="base_version"),
        CheckConstraint("jsonb_typeof(\"entries\") = 'array'", name="entries"),
        CheckConstraint('"status" = \'PENDING\' OR "reviewedAt" IS NOT NULL', name="reviewed"),
        CheckConstraint('("status" = \'APPROVED\') = ("layoutVersion" IS NOT NULL)', name="written"),
        Index(None, "status", "createdAt"),
        Index(None, "proposerId"),
        Index(None, "craftId"),
        Index(None, "categoryId"),
        Index(None, "reviewedById"),
    )
