import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, one_of, updated_at, uuid_pk
from app.models.enums import NOTIFICATION_KINDS

NOTIFICATION_KIND_CHARS = 32
ONE_UNREAD_INDEX = "Notification_one_unread_key"


class Notification(Base):
    __tablename__ = "Notification"

    id: Mapped[uuid.UUID] = uuid_pk()
    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(NOTIFICATION_KIND_CHARS), nullable=False)
    explainerId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("Answer.id", ondelete="CASCADE"), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    readAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    createdAt: Mapped[datetime] = created_at()
    updatedAt: Mapped[datetime] = updated_at()

    __table_args__ = (
        CheckConstraint(one_of("kind", NOTIFICATION_KINDS), name="kind"),
        Index(None, "userId", "createdAt"),
        Index(None, "explainerId"),
        Index(
            ONE_UNREAD_INDEX,
            "userId",
            "explainerId",
            "kind",
            unique=True,
            postgresql_where=text('"readAt" IS NULL'),
        ),
    )


class AlertDigestSend(Base):
    __tablename__ = "AlertDigestSend"

    id: Mapped[uuid.UUID] = uuid_pk()
    userId: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    weekOf: Mapped[date] = mapped_column(Date, nullable=False)
    items: Mapped[int] = mapped_column(Integer, nullable=False)
    createdAt: Mapped[datetime] = created_at()

    __table_args__ = (
        UniqueConstraint("userId", "weekOf"),
        CheckConstraint('"items" >= 1', name="items"),
    )
