import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, one_of, uuid_pk
from app.models.monograph_documents import SLUG_CHARS, SUBJECT_KIND_CHARS
from app.models.oauth import CLIENT_NAME_CHARS

__all__ = [
    "HOLD_STATES",
    "HOLD_SUBJECT_KINDS",
    "UNLINK_REASON_CHARS",
    "KnowledgePieceUnlink",
    "PageHold",
]

HOLD_STATES = ("WAITING", "CONFIRMED", "DISCARDED")
HOLD_SUBJECT_KINDS = ("craft", "family", "category")
UNLINK_REASON_CHARS = 500
STATE_CHARS = 16


def _person(ondelete: str = "SET NULL", *, nullable: bool = True) -> Mapped[Any]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("User.id", ondelete=ondelete), nullable=nullable)


def _page_key(column: str) -> Index:
    return Index(
        f"KnowledgePieceUnlink_pieceId_{column}_key",
        "pieceId",
        column,
        unique=True,
        postgresql_where=text(f'"{column}" IS NOT NULL'),
    )


class KnowledgePieceUnlink(Base):
    __tablename__ = "KnowledgePieceUnlink"

    id: Mapped[uuid.UUID] = uuid_pk()
    pieceId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("KnowledgePiece.id", ondelete="CASCADE"), nullable=False
    )
    craftId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Craft.id", ondelete="CASCADE")
    )
    categoryId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("CraftCategory.id", ondelete="CASCADE")
    )
    unlinkedById: Mapped[uuid.UUID | None] = _person()
    reason: Mapped[str | None] = mapped_column(String(UNLINK_REASON_CHARS))
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (
        CheckConstraint('("craftId" IS NULL) <> ("categoryId" IS NULL)', name="one_page"),
        _page_key("craftId"),
        _page_key("categoryId"),
        Index(None, "craftId"),
        Index(None, "categoryId"),
        Index(None, "unlinkedById"),
    )


class PageHold(Base):
    __tablename__ = "PageHold"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = uuid_pk()
    userId: Mapped[uuid.UUID] = _person("CASCADE", nullable=False)
    subjectKind: Mapped[str] = mapped_column(String(SUBJECT_KIND_CHARS), nullable=False)
    subjectSlug: Mapped[str] = mapped_column(String(SLUG_CHARS), nullable=False)
    draftId: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("PageDraft.id", ondelete="SET NULL")
    )
    draftVersion: Mapped[int | None] = mapped_column(Integer)
    bundle: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    clientName: Mapped[str | None] = mapped_column(String(CLIENT_NAME_CHARS))
    previewUrl: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(STATE_CHARS), nullable=False, server_default=text("'WAITING'"))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    critique: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    createdAt: Mapped[datetime] = created_at()
    expiresAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decidedAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(one_of("subjectKind", HOLD_SUBJECT_KINDS), name="subjectKind"),
        CheckConstraint(one_of("state", HOLD_STATES), name="state"),
        CheckConstraint("jsonb_typeof(\"bundle\") = 'object'", name="bundle"),
        CheckConstraint('"expiresAt" > "createdAt"', name="expires"),
        CheckConstraint('("state" = \'WAITING\') = ("decidedAt" IS NULL)', name="decided"),
        CheckConstraint('("state" = \'CONFIRMED\') = ("result" IS NOT NULL)', name="confirmed"),
        Index(
            "PageHold_userId_subject_waiting_key",
            "userId",
            "subjectKind",
            "subjectSlug",
            unique=True,
            postgresql_where=text("\"state\" = 'WAITING'"),
        ),
        Index(None, "userId", "createdAt"),
        Index(None, "draftId"),
    )
