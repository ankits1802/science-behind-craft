import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import enums as e
from app.models.base import Base, created_at, one_of, updated_at, uuid_pk
from app.models.knowledge import FIELD_COLUMN_CHARS

SECTION_STATUS_COLUMN_CHARS = 16
PUBLISHED = "PUBLISHED"
SUBJECT_COLUMNS = ("craftId", "categoryId")


def _version_key(column: str) -> Index:
    return Index(
        f"ArticleSection_{column}_field_version_key",
        column,
        "field",
        "version",
        unique=True,
        postgresql_where=text(f'"{column}" IS NOT NULL'),
    )


def _published_key(column: str) -> Index:
    return Index(
        f"ArticleSection_{column}_field_published_key",
        column,
        "field",
        unique=True,
        postgresql_where=text(f'"{column}" IS NOT NULL AND "status" = \'{PUBLISHED}\''),
    )


class ArticleSection(Base):
    __tablename__ = "ArticleSection"

    id: Mapped[uuid.UUID] = uuid_pk()
    craftId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Craft.id", ondelete="CASCADE")
    )
    categoryId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("CraftCategory.id", ondelete="CASCADE")
    )
    field: Mapped[str] = mapped_column(String(FIELD_COLUMN_CHARS), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    sentences: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(SECTION_STATUS_COLUMN_CHARS), nullable=False, server_default="PROPOSED"
    )
    writtenByKind: Mapped[str] = mapped_column(e.ActorKind, nullable=False, server_default="SYSTEM")
    writtenById: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    reviewedById: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    reviewedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("field", e.DISCIPLINES), name="field"),
        CheckConstraint(one_of("status", e.SECTION_STATUSES), name="status"),
        CheckConstraint('"version" >= 1', name="version"),
        CheckConstraint('("craftId" IS NULL) <> ("categoryId" IS NULL)', name="one_subject"),
        CheckConstraint(
            'jsonb_typeof("sentences") = \'array\' AND jsonb_array_length("sentences") > 0', name="sentences"
        ),
        CheckConstraint('"reviewedById" IS NULL OR "reviewedAt" IS NOT NULL', name="reviewed_by"),
        *(_version_key(column) for column in SUBJECT_COLUMNS),
        *(_published_key(column) for column in SUBJECT_COLUMNS),
        Index(None, "writtenById"),
        Index(None, "reviewedById"),
    )
