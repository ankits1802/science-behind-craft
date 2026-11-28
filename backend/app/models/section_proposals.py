import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import enums as e
from app.models.base import Base, created_at, one_of, updated_at, uuid_pk
from app.models.knowledge import FIELD_COLUMN_CHARS
from app.models.open_work import TASK_KEY_COLUMN_CHARS

__all__ = [
    "SECTION_PROPOSAL_ORIGINS",
    "SECTION_PROPOSAL_STATUSES",
    "SECTION_REVIEW_NOTE_CHARS",
    "SectionProposal",
]

SECTION_PROPOSAL_STATUSES = ("PENDING", "APPROVED", "REJECTED", "REFUSED")
SECTION_PROPOSAL_ORIGINS = ("CONTRIBUTION", "AGENT")
SECTION_REVIEW_NOTE_CHARS = 500
CODE_CHARS = 16


def _person() -> Mapped[uuid.UUID | None]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL"))


class SectionProposal(Base):
    __tablename__ = "SectionProposal"

    id: Mapped[uuid.UUID] = uuid_pk()
    proposerId: Mapped[uuid.UUID | None] = _person()
    craftId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Craft.id", ondelete="CASCADE")
    )
    categoryId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("CraftCategory.id", ondelete="CASCADE")
    )
    field: Mapped[str] = mapped_column(String(FIELD_COLUMN_CHARS), nullable=False)
    sentences: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    taskKey: Mapped[str | None] = mapped_column(String(TASK_KEY_COLUMN_CHARS))
    note: Mapped[str | None] = mapped_column(String(SECTION_REVIEW_NOTE_CHARS))
    origin: Mapped[str] = mapped_column(String(CODE_CHARS), nullable=False)
    status: Mapped[str] = mapped_column(String(CODE_CHARS), nullable=False, server_default="PENDING")
    reviewedById: Mapped[uuid.UUID | None] = _person()
    reviewedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewNote: Mapped[str | None] = mapped_column(String(SECTION_REVIEW_NOTE_CHARS))
    sectionId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ArticleSection.id", ondelete="SET NULL")
    )
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("field", e.DISCIPLINES), name="field"),
        CheckConstraint(one_of("status", SECTION_PROPOSAL_STATUSES), name="status"),
        CheckConstraint(one_of("origin", SECTION_PROPOSAL_ORIGINS), name="origin"),
        CheckConstraint(
            'jsonb_typeof("sentences") = \'array\' AND jsonb_array_length("sentences") > 0', name="sentences"
        ),
        CheckConstraint("jsonb_typeof(\"checks\") = 'array'", name="checks"),
        CheckConstraint(
            "\"status\" IN ('PENDING', 'REFUSED') OR \"reviewedAt\" IS NOT NULL", name="reviewed"
        ),
        CheckConstraint('num_nonnulls("craftId", "categoryId") = 1', name="subject"),
        Index(None, "status", "createdAt"),
        Index(None, "proposerId"),
        Index(None, "craftId"),
        Index(None, "categoryId"),
        Index(None, "reviewedById"),
        Index(None, "sectionId"),
    )
