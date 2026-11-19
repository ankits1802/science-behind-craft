import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import enums as e
from app.models.base import Base, created_at, uuid_pk

__all__ = ["LAYOUT_SUBJECT_COLUMNS", "PageLayout"]

LAYOUT_SUBJECT_COLUMNS = ("craftId", "categoryId")


def _version_key(column: str) -> Index:
    return Index(
        f"PageLayout_{column}_version_key",
        column,
        "version",
        unique=True,
        postgresql_where=text(f'"{column}" IS NOT NULL'),
    )


class PageLayout(Base):
    __tablename__ = "PageLayout"

    id: Mapped[uuid.UUID] = uuid_pk()
    craftId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Craft.id", ondelete="CASCADE")
    )
    categoryId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("CraftCategory.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    entries: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    writtenByKind: Mapped[str] = mapped_column(e.ActorKind, nullable=False, server_default="SYSTEM")
    writtenById: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="SET NULL")
    )
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (
        CheckConstraint('"version" >= 1', name="version"),
        CheckConstraint('("craftId" IS NULL) <> ("categoryId" IS NULL)', name="one_subject"),
        CheckConstraint("jsonb_typeof(\"entries\") = 'array'", name="entries"),
        *(_version_key(column) for column in LAYOUT_SUBJECT_COLUMNS),
        Index(None, "writtenById"),
    )
