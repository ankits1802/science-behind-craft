import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, one_of, uuid_pk
from app.models.monograph_documents import SLUG_CHARS, SUBJECT_KIND_CHARS
from app.models.page_previews import PREVIEW_SUBJECT_KINDS

__all__ = [
    "DRAWN_SIDES",
    "ORIGIN_CHARS",
    "PICTURE_NAME_CHARS",
    "SIDE_CHARS",
    "DrawnPicture",
    "PageProposal",
]

DRAWN_SIDES = ("BEFORE", "AFTER")
SIDE_CHARS = 8
ORIGIN_CHARS = 16
PICTURE_NAME_CHARS = 80


class PageProposal(Base):
    __tablename__ = "PageProposal"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = uuid_pk()
    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    subjectKind: Mapped[str] = mapped_column(String(SUBJECT_KIND_CHARS), nullable=False)
    subjectSlug: Mapped[str] = mapped_column(String(SLUG_CHARS), nullable=False)
    origin: Mapped[str] = mapped_column(String(ORIGIN_CHARS), nullable=False)
    parts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
    decisions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    createdAt: Mapped[datetime] = created_at()
    closedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(one_of("subjectKind", PREVIEW_SUBJECT_KINDS), name="subjectKind"),
        CheckConstraint("jsonb_typeof(\"parts\") = 'array'", name="parts"),
        CheckConstraint("jsonb_typeof(\"changes\") = 'array'", name="changes"),
        CheckConstraint("jsonb_typeof(\"decisions\") = 'array'", name="decisions"),
        Index(None, "userId", "createdAt"),
        Index(None, "closedAt", "createdAt"),
    )


class DrawnPicture(Base):
    __tablename__ = "DrawnPicture"

    id: Mapped[uuid.UUID] = uuid_pk()
    previewId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("PagePreview.id", ondelete="CASCADE"), nullable=True
    )
    proposalId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("PageProposal.id", ondelete="CASCADE"), nullable=True
    )
    side: Mapped[str] = mapped_column(String(SIDE_CHARS), nullable=False)
    name: Mapped[str] = mapped_column(String(PICTURE_NAME_CHARS), nullable=False)
    caption: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, deferred=True)
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (
        CheckConstraint('("previewId" IS NULL) <> ("proposalId" IS NULL)', name="one_owner"),
        CheckConstraint(one_of("side", DRAWN_SIDES), name="side"),
        CheckConstraint('"width" >= 1 AND "height" >= 1', name="size"),
        Index(None, "previewId"),
        Index(None, "proposalId", "side"),
    )
